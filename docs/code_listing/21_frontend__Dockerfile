# Build both React apps, then serve them with Nginx (build context: project root)
FROM node:20-alpine AS build
WORKDIR /src
COPY frontend/widget/package*.json widget/
RUN cd widget && npm ci --no-audit --no-fund
COPY frontend/admin/package*.json admin/
RUN cd admin && npm ci --no-audit --no-fund
COPY frontend/widget widget
COPY frontend/admin admin
RUN cd widget && npm run build && cd ../admin && npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/widget/dist/widget.js /usr/share/nginx/html/widget.js
COPY --from=build /src/admin/dist /usr/share/nginx/html/admin
COPY docs/demo-college-site.html /usr/share/nginx/html/index.html
# Serve the widget from this same host
RUN sed -i 's#http://localhost:8088/widget.js#/widget.js#' /usr/share/nginx/html/index.html
EXPOSE 80
