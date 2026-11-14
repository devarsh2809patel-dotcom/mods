"""Build the standalone Stock Catalogue Studio: one HTML file, no Claude needed.

    python build_standalone.py            -> ../standalone/Stock_Catalogue_Studio.html

The PDF libraries and the starting data (seed/) are embedded, so the file works offline.
After the first open, the browser keeps your own data; the seed is only the starting point.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "standalone", "Stock_Catalogue_Studio.html")


def js(name):
    code = open(os.path.join(HERE, "vendor", name), encoding="utf-8").read()
    return code.replace("</script", "<\\/script")


def seed():
    data = {"format": "stock-studio", "companies": {}, "sections": {}, "versions": {}}
    for kind in ("companies", "sections"):
        folder = os.path.join(HERE, "seed", kind)
        for f in sorted(os.listdir(folder)):
            data[kind][f[:-5]] = json.load(open(os.path.join(folder, f), encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


page = open(os.path.join(HERE, "stock-studio.html"), encoding="utf-8").read()
page = re.sub(r'<script src="[^"]*jspdf\.umd\.min\.js"></script>',
              lambda m: "<script>" + js("jspdf-2.5.1.umd.min.js") + "</script>", page)
page = re.sub(r'<script src="[^"]*jspdf\.plugin\.autotable\.min\.js"></script>',
              lambda m: "<script>" + js("jspdf-autotable-3.8.2.min.js") + "</script>", page)
assert "cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js\"></script>" not in page, "library tags not replaced"
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>'
        '<script>window.__SEED__=' + seed() + '</script></head><body>')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(head + page + "</body></html>")
print("wrote", os.path.normpath(OUT), os.path.getsize(OUT) // 1024, "KB")
