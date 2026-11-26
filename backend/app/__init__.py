"""Flask application factory."""
import click
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.extensions import db, limiter, login_manager


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    # Public chat endpoints may be called from any college site embedding the widget (FR-08);
    # admin endpoints rely on same-origin cookies served through Nginx.
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

    from models import AdminUser

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(AdminUser, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify(error="authentication required"), 401

    from routes.admin import admin_bp
    from routes.public import public_bp

    app.register_blueprint(public_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    from routes.site import frontend_available, site_bp
    if app.config.get("SERVE_FRONTEND") and frontend_available():
        app.register_blueprint(site_bp)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify(error=err.description if isinstance(err.description, str) else err.name), err.code

    @app.errorhandler(Exception)
    def handle_error(err):
        app.logger.exception("Unhandled error")
        return jsonify(error="internal server error"), 500

    @app.cli.command("purge-logs")
    @click.option("--days", type=int, default=None, help="Retention period (default LOG_RETENTION_DAYS)")
    def purge_logs(days):
        """Remove the free text of queries older than the retention period (Table 19)."""
        from app.privacy import purge_old_query_text
        days = days if days is not None else app.config["LOG_RETENTION_DAYS"]
        click.echo(f"query_text removed from {purge_old_query_text(days)} log row(s) older than {days} days")

    with app.app_context():
        from app.seed import seed_all
        db.create_all()
        seed_all()
        if app.config.get("WARMUP_NLP", True):
            from app.nlp_service import get_engine
            get_engine()  # build indexes and load SBERT before the first request

    return app
