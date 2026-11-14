"""End-to-end QA. Tests the generated PDF / HTML files, not the templates.

Run:  python qa/run_qa.py
Uses a throw-away database and output folder; your real data is not touched.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypdf import PdfReader  # noqa: E402

from app.web import create_app  # noqa: E402

FORBIDDEN = ["high court", "loha bhavan", "ashram road", "income tax"]
results = []


def check(n, label, ok, detail=""):
    results.append((n, label, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {n:>2}. {label}" + (f"  -- {detail}" if detail and not ok else ""))


def latest(out, slug, ext):
    folder = os.path.join(out, slug)
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(f"LATEST.{ext}")][0]


def pdf_facts(path):
    r = PdfReader(path)
    pages = [p.extract_text() or "" for p in r.pages]
    page_ids = {p.indirect_reference.idnum: i for i, p in enumerate(r.pages)}
    links = []  # (page_index, kind, target page index or URI)
    for i, p in enumerate(r.pages):
        for a in p.get("/Annots") or []:
            a = a.get_object()
            if a.get("/Subtype") != "/Link":
                continue
            act = a.get("/A")
            if act is not None:
                act = act.get_object()
                if act.get("/S") == "/URI":
                    links.append((i, "uri", str(act["/URI"])))
            elif a.get("/Dest") is not None:
                links.append((i, "goto", page_ids.get(a["/Dest"][0].idnum)))
    meta = " ".join(str(v) for v in (r.metadata or {}).values())
    outline = [o.title for o in r.outline if hasattr(o, "title")]
    layout = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    return dict(reader=r, pages=pages, links=links, meta=meta, outline=outline, layout=layout)


def main():
    tmp = tempfile.mkdtemp(prefix="stockqa-")
    db, out = os.path.join(tmp, "inventory.db"), os.path.join(tmp, "output")
    app = create_app(db, out)
    store = app.config["STORE"]
    cl = app.test_client()
    comps = {c["slug"]: c for c in store.companies()}
    expected_numbers = {"cd-patel": {"919925007731", "917048487731"},
                        "daksh": {"919925007731", "919825058831"}}

    # 1-3 data capture & separation -----------------------------------------
    counts = {s: store.stats(c["id"])["total"] for s, c in comps.items()}
    check(1, "All screenshot tables loaded (8 categories: RHS, SHS, CHS, angles, flats, round-edge flats, round & square bars)",
          len(store.categories()) == 8, str(len(store.categories())))
    check(2, "All 442 extracted articles present per firm", all(v == 442 for v in counts.values()), str(counts))
    ids = {s: {a["id"] for a in store.articles(company_id=c["id"])} for s, c in comps.items()}
    check(3, "Two firms have separate inventories (no shared records)",
          not (ids["cd-patel"] & ids["daksh"]) and len(comps) == 2)

    # generate via the UI ------------------------------------------------------
    r = cl.post("/brochures/generate", data={"company": "all", "kind": "both"})
    check(15, "Generate-both action works", r.status_code == 302)
    facts, htmls = {}, {}
    for slug in comps:
        facts[slug] = pdf_facts(latest(out, slug, "pdf"))
        htmls[slug] = open(latest(out, slug, "html"), encoding="utf-8").read()

    # 4-6 addresses / placeholders ---------------------------------------------
    bad = []
    for slug, f in facts.items():
        blob = (" ".join(f["pages"]) + " " + f["meta"]).lower()
        hblob = htmls[slug].lower()
        raw = open(latest(out, slug, "pdf"), "rb").read().lower()
        for w in FORBIDDEN:
            if w in blob or w in hblob or w.encode() in raw:
                bad.append(f"{slug}:{w}")
    check(4, "Old High Court / Loha Bhavan / Ashram Road address absent (PDF text, metadata, raw bytes, web)", not bad, str(bad))
    check(5, "Navapura godown address present in both PDFs and web catalogues",
          all("Navapura" in " ".join(f["pages"]) for f in facts.values()) and all("Navapura" in h for h in htmls.values()))
    ph = [ct["name"] for c in comps.values() for ct in store.contacts(c["id"]) if ct["is_placeholder"]]
    leaked = [s for s, f in facts.items() if "to be provided" in " ".join(f["pages"]).lower()]
    check(6, "Third contact kept as a clearly marked placeholder in the tool, not printed for customers",
          len(ph) == 2 and not leaked, f"placeholders={ph}, leaked={leaked}")

    # 7 legibility: every article row is rendered as text -----------------------
    missing = {}
    for slug, c in comps.items():
        text = " ".join(facts[slug]["pages"])
        miss = [a["sku"] for a in store.articles(company_id=c["id"]) if a["sku"] not in text]
        if miss:
            missing[slug] = miss[:5]
    check(7, "Every article code + dimensions rendered as real text in its firm's PDF", not missing, str(missing))

    # 8 availability not fabricated ----------------------------------------------
    t = " ".join(facts["cd-patel"]["pages"])
    av_rows = len(re.findall(r"\bAVAILABLE\b", t.replace("UNCONFIRMED", "")))
    check(8, "Availability not fabricated: all seeded articles show UNCONFIRMED",
          store.stats(1)["available"] == 0 and t.count("UNCONFIRMED") >= 442, f"available words={av_rows}")

    # 9 search ------------------------------------------------------------------
    terms = ["50x50", "50 x 50", "40 x 20", "25 mm (1\")", "SHS-50X50-2.0", "Angle", "IS 4923"]
    found = {term: any(term.lower() in p.lower() for p in facts["cd-patel"]["pages"]) for term in terms}
    check(9, "PDF text search finds sizes / codes / specs", all(found.values()), str(found))

    # 10 TOC + header links ---------------------------------------------------------
    toc_ok, problems = True, []
    for slug, f in facts.items():
        toc_links = [l[2] for l in f["links"] if l[0] == 1 and l[1] == "goto"]
        cats = [c["name"] for c in store.categories()]
        landed = []
        for pg in toc_links:
            hit = [c for c in cats if pg is not None and f["pages"][pg].count(c) >= 1 and "SECTION" in f["pages"][pg]]
            landed.append(hit)
        if len([x for x in landed if x]) < 8:
            toc_ok = False; problems.append(f"{slug}: {landed}")
        # each section's TOC link must land on the page where that section starts
        for c in cats:
            pages_with_title = [i for i, p in enumerate(f["pages"]) if f"{c}\n" in p and "SECTION" in p]
            if not pages_with_title or pages_with_title[0] not in toc_links:
                toc_ok = False; problems.append(f"{slug}: {c} start page not linked")
        back = {l[0] for l in f["links"] if l[1] == "goto" and l[2] == 1 and l[0] >= 1}
        if back != set(range(1, len(f["pages"]))):
            toc_ok = False; problems.append(f"{slug}: back links on {sorted(back)}")
        if len(f["outline"]) < 9:
            toc_ok = False; problems.append(f"{slug}: outline {len(f['outline'])}")
    check(10, "Contents links land on the right section page; 'Contents' button on every page; PDF bookmarks", toc_ok, str(problems))

    # 11 WhatsApp links -----------------------------------------------------------
    wa_ok, wa_problems = True, []
    for slug, f in facts.items():
        uris = [l[2] for l in f["links"] if l[1] == "uri" and "wa.me" in l[2]]
        nums = {urlparse(u).path.strip("/") for u in uris}
        if nums != expected_numbers[slug]:
            wa_ok = False; wa_problems.append(f"{slug}: numbers {nums}")
        enquire = [u for u in uris if "Article%20code" in u or "Article code" in unquote(u)]
        if len(enquire) != counts[slug]:
            wa_ok = False; wa_problems.append(f"{slug}: {len(enquire)} enquire links")
        msg = parse_qs(urlparse(enquire[0]).query)["text"][0]
        if not all(k in msg for k in ("Article:", "Size:", "Quantity Required:", "confirm availability and pricing")):
            wa_ok = False; wa_problems.append("prefill text")
        if comps[slug]["name"] not in msg:
            wa_ok = False; wa_problems.append("company name missing in message")
    check(11, "WhatsApp links use the right firm's numbers (wa.me/91...) with a pre-filled enquiry per article", wa_ok, str(wa_problems))

    # 12 copyable text --------------------------------------------------------------
    line = next((ln for ln in facts["cd-patel"]["layout"].splitlines() if "RHS-40X20-1.2" in ln), "")
    copy_btns = htmls["cd-patel"].count('class="btn cp"')
    check(12, "Article rows are selectable text; web catalogue has a Copy button per article",
          "40 x 20" in line and "1.06" in line and copy_btns == 442, f"line='{line}', copy={copy_btns}")

    # 13 CTA on every page ------------------------------------------------------------
    cta_ok = all(all(comps[s]["footer_cta"] in p for p in f["pages"]) and
                 all(any(l[0] == i and l[1] == "uri" and "wa.me" in l[2] for l in f["links"]) for i in range(len(f["pages"])))
                 for s, f in facts.items())
    check(13, "Every page has the WhatsApp enquiry CTA with clickable contacts", cta_ok)

    # 14 adding an article updates the brochure ------------------------------------------
    shs = store.category("shs")["id"]
    r = cl.post("/articles/new", data={"company_id": [str(comps["daksh"]["id"])], "category_id": str(shs),
                                       "size": "45x45", "thickness_mm": "2.0", "weight_kg_m": "2.62",
                                       "availability": "available"})
    dup = cl.post("/articles/new", data={"company_id": [str(comps["daksh"]["id"])], "category_id": str(shs),
                                         "size": "45 x 45", "thickness_mm": "2", "availability": "available"})
    dup_blocked = b"Duplicate" in dup.data
    a = store.find_by_sku(comps["daksh"]["id"], "SHS-45X45-2.0")
    cl.post(f"/articles/{store.find_by_sku(comps['daksh']['id'], 'SHS-50X50-2.0')['id']}/availability",
            data={"availability": "out_of_stock"})
    cl.post("/brochures/generate", data={"company": "daksh", "kind": "both"})
    fd = pdf_facts(latest(out, "daksh", "pdf"))
    txt = fd["layout"]
    row = next((ln for ln in txt.splitlines() if re.match(r"\s*SHS-45X45-2\.0\s", ln)), "")
    row2 = next((ln for ln in txt.splitlines() if re.match(r"\s*SHS-50X50-2\.0\s", ln)), "")
    in_cd = "SHS-45X45-2.0" in " ".join(pdf_facts(latest(out, "cd-patel", "pdf"))["pages"])
    check(14, "New article + availability change appear after regeneration (and duplicates are blocked)",
          a and "AVAILABLE" in row and "OUT OF STOCK" in row2 and dup_blocked and not in_cd and
          "SHS-45X45-2.0" in open(latest(out, "daksh", "html"), encoding="utf-8").read(),
          f"row='{row}' row2='{row2}' dup={dup_blocked} in_cd={in_cd}")

    # 15 independent exports ------------------------------------------------------------
    before = {s: len(os.listdir(os.path.join(out, s))) for s in comps}
    cl.post("/brochures/generate", data={"company": "cd-patel", "kind": "pdf"})
    after = {s: len(os.listdir(os.path.join(out, s))) for s in comps}
    check(15, "Each firm's PDF exports independently (one firm only touches its own files)",
          after["cd-patel"] == before["cd-patel"] + 1 and after["daksh"] == before["daksh"])

    # import flow ------------------------------------------------------------------------
    csv_text = ("company,category,article_code,size,thickness_mm,weight_kg_m,availability\n"
                "cd-patel,rhs,RHS-40X20-1.2,,,,Available\n"
                "both,channels,,75 x 40,,,Available\n"
                "cd-patel,shs,,44x44,2.0,2.5,yes\n"
                "cd-patel,shs,,44 x 44,2.0,,\n")
    r = cl.post("/import", data={"file": (io.BytesIO(csv_text.encode()), "t.csv")},
                content_type="multipart/form-data")
    body = r.data.decode()
    token = re.search(r'name="token" value="(\w+)"', body).group(1)
    preview_ok = "Unknown category" in body and "Duplicate of row 4" in body and ">UPDATE<" in body
    before_wt = store.find_by_sku(1, "RHS-40X20-1.2")["weight_kg_m"]
    cl.post("/import/confirm", data={"token": token})
    upd = store.find_by_sku(1, "RHS-40X20-1.2")
    new = store.find_by_sku(1, "SHS-44X44-2.0")
    check("I", "Import: preview flags errors/duplicates; update changes only filled columns; new rows added",
          preview_ok and upd["availability"] == "available" and upd["weight_kg_m"] == before_wt and new
          and new["availability"] == "available")

    # company edit -------------------------------------------------------------------------
    d = comps["daksh"]
    cts = store.contacts(d["id"])
    form = {"name": d["name"], "tagline": d["tagline"], "email": d["email"], "website": "",
            "primary_color": d["primary_color"], "accent_color": d["accent_color"], "footer_cta": d["footer_cta"],
            "addr_label": [a["label"] for a in store.addresses(d["id"])], "addr_text": [a["text"] for a in store.addresses(d["id"])],
            "ct_name": [c["name"] for c in cts[:2]] + ["Test Person"], "ct_phone": [c["phone"] for c in cts[:2]] + ["9876543210"],
            "primary_contact": "0"}
    cl.post(f"/companies/{d['slug']}", data=form)
    pdf, _, _ = __import__("app.brochure_pdf", fromlist=["x"]).render(
        __import__("app.catalogue", fromlist=["x"]).build(store, "daksh"))
    p0 = PdfReader(io.BytesIO(pdf)).pages[3].extract_text()
    check("C", "Company details are editable and flow into the brochure (third contact appears once filled)",
          "Test Person" in p0 and "+91 98765 43210" in p0)

    # delete with confirmation ----------------------------------------------------------------
    aid = new["id"]
    r1 = cl.post(f"/articles/{aid}/delete", data={})
    r2 = cl.post(f"/articles/{aid}/delete", data={"confirm": "yes"})
    check("D", "Delete requires confirmation", r1.status_code == 400 and r2.status_code == 302 and not store.article(aid))

    # 16 persistence --------------------------------------------------------------------------
    store.db.close()
    app2 = create_app(db, out)
    s2 = app2.config["STORE"]
    check(16, "Data persists after restarting the app (new process state, same database)",
          s2.find_by_sku(comps["daksh"]["id"], "SHS-45X45-2.0") is not None and
          s2.find_by_sku(1, "RHS-40X20-1.2")["availability"] == "available")

    # pages that render ------------------------------------------------------------------------
    c2 = app2.test_client()
    pages_ok = all(c2.get(u).status_code == 200 for u in
                   ["/", "/articles", "/articles?company=1&flagged=1", "/articles/new", "/import", "/brochures",
                    "/companies/cd-patel", "/import/template.csv", "/import/template.xlsx", "/export.csv",
                    "/brochures/preview/daksh.pdf", "/brochures/preview/cd-patel.html"])
    check("P", "All management pages, templates, exports and previews respond", pages_ok)

    failed = [r for r in results if not r[2]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed. Temp files: {tmp}")
    if not failed:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
