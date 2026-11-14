"""CSV / Excel import with a validate-then-confirm flow.

Update rule: an existing article (same company + article code) is updated only in the
columns that have a value in the file. Blank cells keep the current value, so a file with
just article_code + availability changes availability and nothing else.
Type CLEAR in a cell to empty that field on purpose.
"""
import csv
import io
import json
import os
import uuid

from . import validation as V
from .store import ARTICLE_FIELDS

TEMPLATE_COLUMNS = ["company", "category", "article_code", "article_name", "size", "nominal_bore",
                    "od_mm", "thickness_mm", "pipe_class", "weight_kg_m", "weight_kg_pc",
                    "specification", "availability", "quantity", "quantity_unit", "notes"]
COL_TO_FIELD = {"article_code": "sku", "article_name": "name"}
EXAMPLES = [
    ["cd-patel", "shs", "", "", "40 x 40", "", "", "2.0", "", "2.29", "13.74", "IS 4923", "Available", "120", "pcs",
     "Example only - delete this row"],
    ["both", "angles", "", "", "50 x 50 x 6", "", "", "", "", "4.5", "", "", "Out of stock", "", "", "Example: 'both' adds to both firms"],
    ["daksh", "rhs", "RHS-40X20-1.2", "", "", "", "", "", "", "", "", "", "Available", "", "",
     "Example: update only availability of an existing article"],
]


def template_csv(store):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_COLUMNS)
    for r in EXAMPLES:
        w.writerow(r)
    return buf.getvalue()


def template_xlsx(store):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Import"
    ws.append(TEMPLATE_COLUMNS)
    for r in EXAMPLES:
        ws.append(r)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="13294B")
    for i, col in enumerate(TEMPLATE_COLUMNS, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = max(12, len(col) + 4)
    help_ws = wb.create_sheet("Help")
    help_ws.append(["Column", "Meaning"])
    rows = [
        ("company", "Company code: " + ", ".join(c["slug"] for c in store.companies()) + ", or 'both'"),
        ("category", "Category code: " + ", ".join(c["slug"] for c in store.categories())),
        ("article_code", "Leave blank for new articles (generated automatically). Fill to update an existing article."),
        ("article_name", "Leave blank to generate from category + size."),
        ("size", "e.g. 40 x 20 (mm). For pipes, 25 NB."),
        ("nominal_bore", "Pipes only, e.g. 25 mm (1\")"),
        ("thickness_mm / od_mm", "Numbers in mm"),
        ("pipe_class", "L, M, H or blank"),
        ("availability", "Available, Out of stock, or Unconfirmed (blank = Unconfirmed for new articles)"),
        ("Blank cells", "When updating, blank cells keep the current value. Type CLEAR to empty a field."),
    ]
    for r in rows:
        help_ws.append(list(r))
    help_ws.column_dimensions["A"].width = 22
    help_ws.column_dimensions["B"].width = 100
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def read_rows(filename, data):
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = [str(h or "").strip().lower() for h in next(it)]
        rows = []
        for vals in it:
            if vals is None or all(v is None or str(v).strip() == "" for v in vals):
                rows.append(None)
                continue
            rows.append({header[i]: ("" if v is None else v) for i, v in enumerate(vals) if i < len(header)})
        return header, rows
    if name.endswith(".csv"):
        text = data.decode("utf-8-sig", errors="replace")
        rd = csv.reader(io.StringIO(text))
        header = [h.strip().lower() for h in next(rd)]
        rows = []
        for vals in rd:
            if not any(v.strip() for v in vals):
                rows.append(None)
                continue
            rows.append({header[i]: v for i, v in enumerate(vals) if i < len(header)})
        return header, rows
    raise ValueError("Upload a .csv or .xlsx file.")


def _resolve(lookup, value):
    v = str(value or "").strip().lower()
    return lookup.get(v)


def analyse(store, header, rows):
    """Return list of planned actions; nothing is written."""
    missing = [c for c in ("company", "category") if c not in header]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. Download the template.")
    unknown = [h for h in header if h and h not in TEMPLATE_COLUMNS]
    companies = {}
    for c in store.companies():
        companies[c["slug"].lower()] = [c]
        companies[c["name"].lower()] = [c]
    companies["both"] = companies["all"] = list(store.companies())
    cats = {}
    for c in store.categories():
        for k in (c["slug"], c["name"], c["prefix"], c["short"]):
            cats[str(k).lower()] = c
    plan, seen = [], {}
    for idx, raw in enumerate(rows, start=2):
        if raw is None:
            continue
        raw = {k: ("" if v is None else str(v).strip() if not isinstance(v, (int, float)) else v)
               for k, v in raw.items() if k in TEMPLATE_COLUMNS}
        comps = _resolve(companies, raw.get("company"))
        cat = _resolve(cats, raw.get("category"))
        if not comps:
            plan.append(dict(row=idx, action="error", error=f"Unknown company '{raw.get('company')}'", company="", sku="", name=""))
            continue
        if not cat:
            plan.append(dict(row=idx, action="error", error=f"Unknown category '{raw.get('category')}'", company="", sku="", name=""))
            continue
        given = {}
        for col, v in raw.items():
            if col in ("company", "category"):
                continue
            field = COL_TO_FIELD.get(col, col)
            if field not in ARTICLE_FIELDS:
                continue
            if isinstance(v, str) and v == "":
                continue
            given[field] = None if (isinstance(v, str) and v.upper() == "CLEAR") else v
        given["category_id"] = cat["id"]
        for comp in comps:
            entry = dict(row=idx, company=comp["name"], company_id=comp["id"], data=given)
            try:
                sku = str(given.get("sku") or "").upper().replace(" ", "")
                existing = store.find_by_sku(comp["id"], sku) if sku else None
                if not existing:
                    probe = store.clean_article(dict(given))
                    existing = store.find_by_sku(comp["id"], probe["sku"])
                if existing:
                    if existing["category_id"] != cat["id"]:
                        raise ValueError(f"Article {existing['sku']} exists in a different category.")
                    merged = store.clean_article(dict(given), existing)
                    changes = []
                    for f in ARTICLE_FIELDS + ["check_note"]:
                        if f in merged and merged[f] != existing[f] and not (merged[f] in (None, "") and existing[f] in (None, "")):
                            if f != "check_note":
                                changes.append(f"{f}: {existing[f]!r} -> {merged[f]!r}")
                    entry.update(action="update" if changes else "unchanged", article_id=existing["id"],
                                 sku=merged["sku"], name=merged["name"], changes=changes)
                    key = (comp["id"], merged["sku"])
                else:
                    a = store.clean_article(dict(given))
                    entry.update(action="new", sku=a["sku"], name=a["name"], changes=[],
                                 warning=a["check_note"])
                    key = (comp["id"], a["sku"])
                if key in seen:
                    raise ValueError(f"Duplicate of row {seen[key]} in this file ({key[1]}).")
                seen[key] = idx
            except ValueError as e:
                entry.update(action="error", error=str(e), sku=entry.get("sku", ""), name=entry.get("name", ""))
            plan.append(entry)
    return plan, unknown


def save_plan(folder, plan):
    os.makedirs(folder, exist_ok=True)
    token = uuid.uuid4().hex
    with open(os.path.join(folder, f"{token}.json"), "w") as fh:
        json.dump(plan, fh)
    return token


def load_plan(folder, token):
    if not token.isalnum():
        raise ValueError("Bad import token")
    path = os.path.join(folder, f"{token}.json")
    if not os.path.exists(path):
        raise ValueError("This import preview has expired. Upload the file again.")
    with open(path) as fh:
        return json.load(fh), path


def apply(store, plan):
    """Apply 'new' and 'update' rows. Re-validates each row; returns counts + errors."""
    done = {"new": 0, "update": 0, "skipped": 0, "errors": []}
    for e in plan:
        if e["action"] not in ("new", "update"):
            done["skipped"] += 1
            continue
        try:
            store.save_article(e["company_id"], dict(e["data"]),
                               article_id=e.get("article_id") if e["action"] == "update" else None,
                               commit=False)
            done[e["action"]] += 1
        except ValueError as ex:
            done["errors"].append(f"Row {e['row']} ({e['company']}): {ex}")
    store.db.commit()
    return done


def export_csv(store, company_id=None):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_COLUMNS + ["weight_check"])
    for a in store.articles(company_id=company_id):
        w.writerow([a["company_slug"], a["category_slug"], a["sku"], a["name"], a["size"], a["nominal_bore"],
                    V.fmt_num(a["od_mm"]), V.fmt_thk(a["thickness_mm"]), a["pipe_class"],
                    V.fmt_num(a["weight_kg_m"]), V.fmt_num(a["weight_kg_pc"]), a["specification"],
                    V.AVAILABILITY[a["availability"]], V.fmt_num(a["quantity"]), a["quantity_unit"],
                    a["notes"], a["check_note"]])
    return buf.getvalue()
