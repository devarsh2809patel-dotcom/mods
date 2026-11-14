"""Builds the read-only data model a brochure is rendered from.

Both the PDF and the web catalogue use this, so they always show the same data.
"""
import re
from datetime import datetime
from urllib.parse import quote

from . import validation as V

STATUS_LABEL = {"available": "AVAILABLE", "out_of_stock": "OUT OF STOCK", "unconfirmed": "UNCONFIRMED"}

COLUMN_TITLES = {
    "size": "Size (mm)", "nominal_bore": "Nominal bore", "od_mm": "OD (mm)",
    "thickness_mm": "Thick (mm)", "pipe_class": "Class", "weight_kg_m": "Kg/m",
    "weight_kg_pc": "Kg/pc", "specification": "Specification",
}


def sort_key(a):
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", a["size"] or "")]
    return (nums or [9e9], a["thickness_mm"] or 0, a["id"])


def group_key(slug, a):
    if slug in ("rhs", "shs"):
        return a["size"]
    if slug == "chs":
        return a["nominal_bore"] or a["size"]
    if slug in ("angles", "flats", "flats-round-edge"):
        return (a["size"] or "").split(" x ")[0]
    return a["id"]


def cell_value(a, col):
    v = a[col]
    if col == "thickness_mm":
        return V.fmt_thk(v)
    if col in ("weight_kg_m", "weight_kg_pc"):
        return V.fmt_num(v, 2)
    if col == "od_mm":
        return V.fmt_num(v)
    return v or ""


def spec_text(cat, a):
    parts = []
    if a["specification"]:
        parts.append(a["specification"])
    elif cat["standard"]:
        parts.append(cat["standard"])
    if a["pipe_class"]:
        parts.append({"L": "Light", "M": "Medium", "H": "Heavy"}[a["pipe_class"]] + " class")
    if a["od_mm"]:
        parts.append(f"OD {V.fmt_num(a['od_mm'])} mm")
    if a["thickness_mm"] is not None:
        parts.append(f"Thickness {V.fmt_thk(a['thickness_mm'])} mm")
    if a["weight_kg_m"]:
        parts.append(f"{V.fmt_num(a['weight_kg_m'], 2)} kg/m")
    return ", ".join(parts) or "-"


def copy_text(company, cat, a):
    size = a["nominal_bore"] or a["size"]
    return (f"Article: {a['name']}\n"
            f"Article code: {a['sku']}\n"
            f"Size: {size}\n"
            f"Specification: {spec_text(cat, a)}\n"
            f"Availability: {STATUS_LABEL[a['availability']].title()}\n"
            f"Quantity Required: ")


def enquiry_message(company, cat, a):
    return (f"Hello {company['name']}, I am interested in the following stock article:\n\n"
            + copy_text(company, cat, a) +
            "\n\nPlease confirm availability and pricing.")


def general_message(company):
    return (f"Hello {company['name']}, I saw your stock catalogue and would like to "
            f"enquire about availability and pricing.\n\nArticle: \nSize: \nQuantity Required: ")


def wa_link(phone, text):
    d = V.wa_digits(phone)
    return f"https://wa.me/{d}?text={quote(text)}" if d else ""


def tel_link(phone):
    d = V.wa_digits(phone)
    return f"tel:+{d}" if d else ""


def build(store, company_key):
    company = store.company(company_key)
    if not company:
        raise ValueError("Unknown company")
    cid = company["id"]
    contacts = [dict(c) for c in store.contacts(cid, usable_only=True)]
    if not contacts:
        raise ValueError(f"{company['name']} has no contact with a valid phone number; "
                         "add one under Companies before generating.")
    primary = store.primary_contact(cid)
    for c in contacts:
        c["wa"] = wa_link(c["phone"], general_message(company))
        c["tel"] = tel_link(c["phone"])
        c["digits"] = V.wa_digits(c["phone"])
    addresses = [dict(a) for a in store.addresses(cid) if not a["is_placeholder"] and a["text"].strip()]

    sections = []
    all_articles = store.articles(company_id=cid)
    for cat in store.categories():
        rows = sorted([a for a in all_articles if a["category_id"] == cat["id"]], key=sort_key)
        if not rows:
            continue
        cols = [c for c in cat["columns"].split(",") if c in COLUMN_TITLES]
        items = []
        prev_group, band = object(), 1
        for a in rows:
            g = group_key(cat["slug"], a)
            first = g != prev_group
            if first:
                band = 1 - band
            prev_group = g
            items.append(dict(
                id=a["id"], sku=a["sku"], name=a["name"], availability=a["availability"],
                status=STATUS_LABEL[a["availability"]],
                cells={c: cell_value(a, c) for c in cols},
                size=a["nominal_bore"] or a["size"], spec=spec_text(cat, a),
                first_in_group=first, band=band,
                copy=copy_text(company, cat, a),
                wa=wa_link(primary["phone"], enquiry_message(company, cat, a)),
                search=" ".join([a["sku"], a["name"], a["size"], a["size"].replace(" ", ""),
                                 a["nominal_bore"], spec_text(cat, a)]).lower(),
            ))
        sections.append(dict(
            key=f"sec-{cat['slug']}", slug=cat["slug"], title=cat["name"], short=cat["short"] or cat["name"],
            standard=cat["standard"], description=cat["description"],
            columns=cols, column_titles=[COLUMN_TITLES[c] for c in cols],
            rows=items,
            counts={k: sum(1 for i in items if i["availability"] == k) for k in STATUS_LABEL},
        ))
    stamp = datetime.now()
    return dict(company=dict(company), contacts=contacts, primary=dict(primary), addresses=addresses,
                sections=sections, total=sum(len(s["rows"]) for s in sections),
                generated_at=stamp, generated_label=stamp.strftime("%d %b %Y, %I:%M %p"),
                general_message=general_message(company))
