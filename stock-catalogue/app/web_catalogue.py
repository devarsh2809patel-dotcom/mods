"""Self-contained, searchable HTML catalogue (companion to the PDF)."""
import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import catalogue
from .brochure_pdf import safe_name

_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
                   autoescape=select_autoescape(["html"]))


def render(ctx):
    company = ctx["company"]
    messages = {}
    for s in ctx["sections"]:
        for it in s["rows"]:
            messages[it["id"]] = {"copy": it["copy"],
                                  "msg": f"Hello {company['name']}, I am interested in the following stock article:\n\n"
                                         f"{it['copy']}\n\nPlease confirm availability and pricing."}
    data = json.dumps(messages, ensure_ascii=False).replace("</", "<\\/")
    return _env.get_template("public_catalogue.html").render(ctx=ctx, co=company, messages=data)


def generate(store, company_key, out_root):
    ctx = catalogue.build(store, company_key)
    html = render(ctx)
    co = ctx["company"]
    folder = os.path.join(out_root, co["slug"])
    os.makedirs(folder, exist_ok=True)
    stamp = ctx["generated_at"].strftime("%Y-%m-%d_%H%M%S")
    path = os.path.join(folder, f"{safe_name(co['name'])}_Web_Catalogue_{stamp}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    latest = os.path.join(folder, f"{safe_name(co['name'])}_Web_Catalogue_LATEST.html")
    shutil.copyfile(path, latest)
    store.log_generation(co["id"], "web", os.path.relpath(path, out_root), ctx["total"])
    return {"path": path, "latest": latest, "articles": ctx["total"], "company": co["name"]}
