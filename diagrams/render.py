"""Render the Mermaid diagrams to PNG with a local copy of mermaid.js and a headless browser.

Setup (once):  cd diagrams/.tools && npm install        (installs mermaid@10.9.1)
Run:           python diagrams/render.py
Writes diagrams/src/<name>.mmd (source) and diagrams/<name>.png (image, 2x resolution).
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from diagram_sources import DIAGRAMS  # noqa: E402

MERMAID_JS = HERE / ".tools" / "node_modules" / "mermaid" / "dist" / "mermaid.min.js"

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff;font-family:'Segoe UI',Tahoma,Arial,sans-serif} #out{display:inline-block;padding:24px}</style>
</head><body><div id="out"></div></body></html>"""


def _trim(path, pad=24):
    """Crop surrounding white space so the diagram fills the figure in the report."""
    from PIL import Image, ImageChops
    img = Image.open(path).convert("RGB")
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, "white")).getbbox()
    if bbox:
        l, t, r, b = bbox
        img.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, img.width), min(b + pad, img.height))).save(path)


def main():
    src_dir = HERE / "src"
    src_dir.mkdir(exist_ok=True)
    only = set(sys.argv[1:])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2, viewport={"width": 1800, "height": 1200})
        page.set_content(PAGE)
        page.add_script_tag(path=str(MERMAID_JS))
        page.evaluate("""() => mermaid.initialize({startOnLoad: false, theme: 'base', securityLevel: 'loose',
            flowchart: {curve: 'basis', htmlLabels: true}, sequence: {mirrorActors: false},
            themeVariables: {primaryColor: '#e6f0f8', primaryBorderColor: '#0b4f8a', primaryTextColor: '#17222d',
              lineColor: '#4a5a6a', secondaryColor: '#e3f4f4', tertiaryColor: '#f6f8fa',
              fontFamily: 'Segoe UI, Tahoma, Arial, sans-serif', fontSize: '15px'}})""")
        for name, code in DIAGRAMS.items():
            if only and name not in only:
                continue
            (src_dir / f"{name}.mmd").write_text(code, encoding="utf-8")
            svg = page.evaluate("async (code) => (await mermaid.render('d' + Date.now(), code)).svg", code)
            page.evaluate("""(svg) => {
                const out = document.getElementById('out');
                out.innerHTML = svg;
                const el = out.querySelector('svg');
                const vb = el.viewBox.baseVal;           // render at the diagram's natural size
                el.style.maxWidth = 'none';
                el.setAttribute('width', vb.width);
                el.setAttribute('height', vb.height);
            }""", svg)
            out = HERE / f"{name}.png"
            page.locator("#out").screenshot(path=str(out))
            _trim(out)
            print("rendered", name)
        browser.close()


if __name__ == "__main__":
    main()
