"""Internal stock management web app (Flask). Run with: python run.py"""
import io
import os

from flask import (Flask, Response, abort, flash, redirect, render_template, request,
                   send_file, send_from_directory, url_for)

from . import brochure_pdf, catalogue, importer, web_catalogue
from . import validation as V
from .store import BASE_DIR, open_store

FIELD_LABELS = {
    "size": "Size (mm)", "nominal_bore": "Nominal bore", "od_mm": "OD (mm)", "thickness_mm": "Thickness (mm)",
    "pipe_class": "Pipe class", "weight_kg_m": "Weight (kg/m)", "weight_kg_pc": "Weight (kg/pc)",
}


def create_app(db_path=None, output_dir=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("STOCK_SECRET", "local-stock-tool")
    store = open_store(db_path)
    out_dir = output_dir or os.environ.get("STOCK_OUTPUT") or os.path.join(BASE_DIR, "output")
    import_dir = os.path.join(os.path.dirname(store.path), "imports")
    os.makedirs(out_dir, exist_ok=True)
    app.config.update(STORE=store, OUTPUT=out_dir)

    @app.context_processor
    def inject():
        return dict(companies=store.companies(), AV=V.AVAILABILITY, categories_all=store.categories())

    def int_or_none(v):
        return int(v) if v and str(v).isdigit() else None

    # ------------------------------------------------------------ dashboard
    @app.route("/")
    def dashboard():
        cards = []
        for c in store.companies():
            placeholders = [ct["name"] for ct in store.contacts(c["id"]) if ct["is_placeholder"]]
            placeholders += [f"{a['label']} address" for a in store.addresses(c["id"]) if a["is_placeholder"]]
            cats = []
            for cat in store.categories():
                rows = store.articles(company_id=c["id"], category_id=cat["id"])
                if rows:
                    cats.append(dict(cat=cat, total=len(rows),
                                     available=sum(r["availability"] == "available" for r in rows),
                                     out=sum(r["availability"] == "out_of_stock" for r in rows)))
            cards.append(dict(c=c, s=store.stats(c["id"]), last=store.last_generation(c["id"]),
                              last_web=store.last_generation(c["id"], "web"),
                              placeholders=placeholders, cats=cats))
        return render_template("dashboard.html", cards=cards)

    # ------------------------------------------------------------ articles
    @app.route("/articles")
    def articles():
        f = dict(company=int_or_none(request.args.get("company")),
                 category=int_or_none(request.args.get("category")),
                 availability=request.args.get("availability") or None,
                 q=(request.args.get("q") or "").strip(),
                 flagged=request.args.get("flagged") == "1")
        if f["availability"] not in (None, *V.AVAILABILITY):
            f["availability"] = None
        rows = store.articles(company_id=f["company"], category_id=f["category"],
                              availability=f["availability"], search=f["q"] or None, flagged=f["flagged"])
        return render_template("articles.html", rows=rows, f=f, args=request.args)

    def form_data():
        d = {k: request.form.get(k, "") for k in
             ("category_id", "name", "sku", "size", "nominal_bore", "od_mm", "thickness_mm", "pipe_class",
              "weight_kg_m", "weight_kg_pc", "specification", "availability", "quantity", "quantity_unit", "notes")}
        return d

    @app.route("/articles/new", methods=["GET", "POST"])
    def article_new():
        if request.method == "POST":
            data = form_data()
            company_ids = request.form.getlist("company_id")
            if not company_ids:
                flash("Choose at least one company.", "error")
                return render_template("article_form.html", a=data, sel_companies=[], is_new=True)
            try:
                saved = []
                for cid in company_ids:
                    store.clean_article(dict(data))  # validate before writing anything
                for cid in company_ids:
                    saved.append(store.save_article(int(cid), dict(data), commit=False))
                store.db.commit()
            except ValueError as e:
                store.db.rollback()
                flash(str(e), "error")
                return render_template("article_form.html", a=data, sel_companies=[int(c) for c in company_ids],
                                       is_new=True)
            a = store.article(saved[0])
            msg = f"Added {a['name']} ({a['sku']})"
            if a["check_note"]:
                msg += f". Check: {a['check_note']}"
            flash(msg + ". Regenerate the brochure to include it.", "ok")
            return redirect(url_for("articles", q=a["sku"]))
        pre = {"availability": "unconfirmed", "category_id": request.args.get("category", "")}
        sel = [int(request.args["company"])] if request.args.get("company", "").isdigit() else []
        return render_template("article_form.html", a=pre, sel_companies=sel, is_new=True)

    @app.route("/articles/<int:aid>/edit", methods=["GET", "POST"])
    def article_edit(aid):
        a = store.article(aid) or abort(404)
        if request.method == "POST":
            data = form_data()
            try:
                store.save_article(int(request.form.get("company_id") or a["company_id"]), data, article_id=aid)
            except ValueError as e:
                flash(str(e), "error")
                merged = dict(a); merged.update(data)
                return render_template("article_form.html", a=merged, sel_companies=[a["company_id"]], is_new=False, aid=aid)
            flash("Saved.", "ok")
            return redirect(request.form.get("next") or url_for("articles"))
        return render_template("article_form.html", a=dict(a), sel_companies=[a["company_id"]], is_new=False, aid=aid,
                               next=request.referrer)

    @app.route("/articles/<int:aid>/delete", methods=["POST"])
    def article_delete(aid):
        a = store.article(aid) or abort(404)
        if request.form.get("confirm") != "yes":
            abort(400)
        store.delete_article(aid)
        flash(f"Deleted {a['name']} ({a['sku']}).", "ok")
        return redirect(request.form.get("next") or url_for("articles"))

    @app.route("/articles/<int:aid>/availability", methods=["POST"])
    def article_availability(aid):
        store.article(aid) or abort(404)
        try:
            store.set_availability([aid], request.form.get("availability"))
        except ValueError as e:
            return Response(str(e), 400)
        if request.headers.get("X-Requested-With") == "fetch":
            return {"ok": True}
        return redirect(request.referrer or url_for("articles"))

    @app.route("/articles/bulk", methods=["POST"])
    def articles_bulk():
        ids = [int(i) for i in request.form.getlist("ids") if i.isdigit()]
        action = request.form.get("action")
        back = request.form.get("next") or url_for("articles")
        if not ids:
            flash("No articles selected.", "error")
            return redirect(back)
        if action == "delete":
            if request.form.get("confirm") != "yes":
                abort(400)
            store.backup("bulk-delete")
            for i in ids:
                store.delete_article(i)
            flash(f"Deleted {len(ids)} articles (backup saved).", "ok")
        elif action in V.AVAILABILITY:
            n = store.set_availability(ids, action)
            flash(f"Marked {n} articles as {V.AVAILABILITY[action]}.", "ok")
        else:
            abort(400)
        return redirect(back)

    # ------------------------------------------------------------ categories
    @app.route("/categories/new", methods=["POST"])
    def category_new():
        try:
            cols = request.form.getlist("columns") or ["size", "weight_kg_m"]
            store.add_category(request.form.get("name", ""), request.form.get("prefix", ""),
                               request.form.get("standard", ""), request.form.get("description", ""),
                               ",".join(c for c in ["size", "nominal_bore", "od_mm", "thickness_mm", "pipe_class",
                                                    "weight_kg_m", "weight_kg_pc"] if c in cols),
                               request.form.get("item_label", ""))
            flash("Category added.", "ok")
        except ValueError as e:
            flash(str(e), "error")
        return redirect(request.referrer or url_for("article_new"))

    # ------------------------------------------------------------ companies
    @app.route("/companies/<slug>", methods=["GET", "POST"])
    def company_edit(slug):
        c = store.company(slug) or abort(404)
        if request.method == "POST":
            fields = {k: request.form.get(k, "") for k in
                      ("name", "tagline", "email", "website", "primary_color", "accent_color", "footer_cta")}
            addrs = [{"label": l, "text": t} for l, t in
                     zip(request.form.getlist("addr_label"), request.form.getlist("addr_text"))]
            primary = request.form.get("primary_contact")
            contacts = [{"name": n, "phone": p, "is_primary": str(i) == primary} for i, (n, p) in
                        enumerate(zip(request.form.getlist("ct_name"), request.form.getlist("ct_phone")))]
            try:
                store.update_company(c["id"], fields, addrs, contacts)
                flash("Company details saved. Regenerate the brochure to apply them.", "ok")
                return redirect(url_for("company_edit", slug=slug))
            except ValueError as e:
                flash(str(e), "error")
        return render_template("company.html", c=store.company(slug), addrs=store.addresses(c["id"]),
                               contacts=store.contacts(c["id"]))

    # ------------------------------------------------------------ import / export
    @app.route("/import", methods=["GET", "POST"])
    def import_page():
        if request.method == "POST":
            f = request.files.get("file")
            if not f or not f.filename:
                flash("Choose a CSV or Excel file.", "error")
                return redirect(url_for("import_page"))
            try:
                header, rows = importer.read_rows(f.filename, f.read())
                plan, unknown = importer.analyse(store, header, rows)
            except Exception as e:  # file parsing errors are shown to the user, not swallowed
                flash(f"Could not read the file: {e}", "error")
                return redirect(url_for("import_page"))
            token = importer.save_plan(import_dir, plan)
            counts = {k: sum(1 for p in plan if p["action"] == k) for k in ("new", "update", "unchanged", "error")}
            return render_template("import.html", plan=plan, counts=counts, token=token, unknown=unknown,
                                   filename=f.filename)
        return render_template("import.html", plan=None)

    @app.route("/import/confirm", methods=["POST"])
    def import_confirm():
        try:
            plan, path = importer.load_plan(import_dir, request.form.get("token", ""))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("import_page"))
        backup = store.backup("before-import")
        res = importer.apply(store, plan)
        os.remove(path)
        msg = f"Import done: {res['new']} added, {res['update']} updated, {res['skipped']} skipped. " \
              f"Backup: {os.path.basename(backup)}"
        flash(msg, "ok")
        for e in res["errors"]:
            flash(e, "error")
        return redirect(url_for("dashboard"))

    @app.route("/import/template.<ext>")
    def import_template(ext):
        if ext == "csv":
            return Response(importer.template_csv(store), mimetype="text/csv",
                            headers={"Content-Disposition": "attachment; filename=stock_import_template.csv"})
        if ext == "xlsx":
            return send_file(io.BytesIO(importer.template_xlsx(store)), as_attachment=True,
                             download_name="stock_import_template.xlsx",
                             mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        abort(404)

    @app.route("/export.csv")
    def export_csv():
        cid = int_or_none(request.args.get("company"))
        name = store.company(cid)["slug"] if cid else "all"
        return Response(importer.export_csv(store, cid), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=inventory_{name}.csv"})

    # ------------------------------------------------------------ brochures
    @app.route("/brochures")
    def brochures():
        info = []
        for c in store.companies():
            folder = os.path.join(out_dir, c["slug"])
            files = sorted((f for f in os.listdir(folder) if "LATEST" not in f), reverse=True) if os.path.isdir(folder) else []
            info.append(dict(c=c, last=store.last_generation(c["id"]), last_web=store.last_generation(c["id"], "web"),
                             files=[f"{c['slug']}/{f}" for f in files][:12],
                             usable=len(store.contacts(c["id"], usable_only=True))))
        return render_template("brochures.html", info=info)

    @app.route("/brochures/generate", methods=["POST"])
    def brochures_generate():
        target = request.form.get("company", "all")
        kinds = request.form.get("kind", "both")
        comps = store.companies() if target == "all" else [store.company(target) or abort(404)]
        for c in comps:
            try:
                if kinds in ("pdf", "both"):
                    r = brochure_pdf.generate(store, c["slug"], out_dir)
                    flash(f"{c['name']}: PDF generated ({r['pages']} pages, {r['articles']} articles).", "ok")
                if kinds in ("web", "both"):
                    web_catalogue.generate(store, c["slug"], out_dir)
                    flash(f"{c['name']}: web catalogue generated.", "ok")
            except Exception as e:  # report and continue with the other company
                app.logger.exception("generation failed for %s", c["slug"])
                flash(f"{c['name']}: generation failed - {e}", "error")
        return redirect(url_for("brochures"))

    @app.route("/brochures/preview/<slug>.pdf")
    def preview_pdf(slug):
        store.company(slug) or abort(404)
        pdf, _, _ = brochure_pdf.render(catalogue.build(store, slug))
        return Response(pdf, mimetype="application/pdf",
                        headers={"Content-Disposition": f"inline; filename=preview_{slug}.pdf"})

    @app.route("/brochures/preview/<slug>.html")
    def preview_web(slug):
        store.company(slug) or abort(404)
        return web_catalogue.render(catalogue.build(store, slug))

    @app.route("/files/<path:fname>")
    def files(fname):
        return send_from_directory(out_dir, fname, as_attachment=request.args.get("dl") == "1")

    return app
