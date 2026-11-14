"""SQLite storage. The database file is the single source of truth for inventory.

Brochure templates only *read* from here, so changing the design never touches stock data.
"""
import os
import shutil
import sqlite3
from datetime import datetime

from . import validation as V

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(BASE_DIR, "data", "inventory.db")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  tagline TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  website TEXT NOT NULL DEFAULT '',
  primary_color TEXT NOT NULL DEFAULT '#13294B',
  accent_color TEXT NOT NULL DEFAULT '#E8A33D',
  footer_cta TEXT NOT NULL DEFAULT 'Interested in a product? WhatsApp us for availability and pricing.',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS addresses (
  id INTEGER PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  text TEXT NOT NULL DEFAULT '',
  is_placeholder INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  phone TEXT NOT NULL DEFAULT '',
  is_placeholder INTEGER NOT NULL DEFAULT 0,
  is_primary INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  prefix TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  item_label TEXT NOT NULL DEFAULT '',
  short TEXT NOT NULL DEFAULT '',
  standard TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  columns TEXT NOT NULL DEFAULT 'size,weight_kg_m',
  sort_order INTEGER NOT NULL DEFAULT 100
);
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES categories(id),
  sku TEXT NOT NULL,
  name TEXT NOT NULL,
  size TEXT NOT NULL DEFAULT '',
  nominal_bore TEXT NOT NULL DEFAULT '',
  od_mm REAL,
  thickness_mm REAL,
  pipe_class TEXT NOT NULL DEFAULT '' CHECK (pipe_class IN ('', 'L', 'M', 'H')),
  weight_kg_m REAL CHECK (weight_kg_m IS NULL OR weight_kg_m > 0),
  weight_kg_pc REAL CHECK (weight_kg_pc IS NULL OR weight_kg_pc > 0),
  specification TEXT NOT NULL DEFAULT '',
  availability TEXT NOT NULL DEFAULT 'unconfirmed'
      CHECK (availability IN ('available', 'out_of_stock', 'unconfirmed')),
  quantity REAL CHECK (quantity IS NULL OR quantity >= 0),
  quantity_unit TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  check_note TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (company_id, sku)
);
CREATE INDEX IF NOT EXISTS ix_articles_company_cat ON articles(company_id, category_id);
CREATE TABLE IF NOT EXISTS generations (
  id INTEGER PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  file_name TEXT NOT NULL,
  article_count INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
"""

ARTICLE_FIELDS = ["category_id", "sku", "name", "size", "nominal_bore", "od_mm", "thickness_mm",
                  "pipe_class", "weight_kg_m", "weight_kg_pc", "specification", "availability",
                  "quantity", "quantity_unit", "notes", "source"]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path=None):
        self.path = path or os.environ.get("STOCK_DB") or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------ helpers
    def q(self, sql, args=()):
        return self.db.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        return self.db.execute(sql, args).fetchone()

    def backup(self, reason):
        folder = os.path.join(os.path.dirname(self.path), "backups")
        os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, f"inventory-{datetime.now():%Y%m%d-%H%M%S}-{reason}.db")
        self.db.commit()
        bk = sqlite3.connect(dest)
        self.db.backup(bk)
        bk.close()
        return dest

    def is_empty(self):
        return self.one("SELECT COUNT(*) c FROM companies")["c"] == 0

    # ------------------------------------------------------------ seeding
    def seed(self):
        from . import seed_data as S
        with self.db:
            for c in S.CATEGORIES:
                self.db.execute(
                    "INSERT INTO categories(slug,prefix,name,item_label,short,standard,description,columns,sort_order)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (c["slug"], c["prefix"], c["name"], c["item_label"], c["short"], c["standard"],
                     c["description"], c["columns"], c["sort_order"]))
            for c in S.COMPANIES:
                cur = self.db.execute(
                    "INSERT INTO companies(slug,name,tagline,email,website,primary_color,accent_color,updated_at)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (c["slug"], c["name"], c["tagline"], c["email"], c["website"],
                     c["primary_color"], c["accent_color"], now()))
                cid = cur.lastrowid
                for i, (label, text, ph) in enumerate(c["addresses"]):
                    self.db.execute("INSERT INTO addresses(company_id,label,text,is_placeholder,sort_order)"
                                    " VALUES (?,?,?,?,?)", (cid, label, text, int(ph), i))
                for i, (name, phone, ph) in enumerate(c["contacts"]):
                    self.db.execute("INSERT INTO contacts(company_id,name,phone,is_placeholder,is_primary,sort_order)"
                                    " VALUES (?,?,?,?,?,?)", (cid, name, phone, int(ph), int(i == 0), i))
        cats = {r["slug"]: r["id"] for r in self.q("SELECT id, slug FROM categories")}
        for comp in self.companies():
            for a in S.build_articles():
                a = dict(a)
                a["category_id"] = cats[a.pop("category")]
                self.save_article(comp["id"], a, commit=False)
        self.db.commit()

    # ------------------------------------------------------------ companies
    def companies(self):
        return self.q("SELECT * FROM companies ORDER BY id")

    def company(self, key):
        col = "id" if isinstance(key, int) or str(key).isdigit() else "slug"
        return self.one(f"SELECT * FROM companies WHERE {col}=?", (key,))

    def addresses(self, company_id):
        return self.q("SELECT * FROM addresses WHERE company_id=? ORDER BY sort_order, id", (company_id,))

    def contacts(self, company_id, usable_only=False):
        rows = self.q("SELECT * FROM contacts WHERE company_id=? ORDER BY sort_order, id", (company_id,))
        if usable_only:
            rows = [r for r in rows if not r["is_placeholder"] and V.wa_digits(r["phone"])]
        return rows

    def update_company(self, company_id, fields, addresses, contacts):
        """addresses/contacts: lists of dicts; rows with empty label/name are dropped."""
        if not (fields.get("name") or "").strip():
            raise ValueError("Company name is required.")
        for c in contacts:
            if c.get("phone", "").strip() and not V.wa_digits(c["phone"]):
                raise ValueError(f"Phone for {c.get('name') or 'contact'} must include a valid number "
                                 f"(10-digit Indian mobile or +country code).")
        with self.db:
            self.db.execute(
                "UPDATE companies SET name=?, tagline=?, email=?, website=?, primary_color=?, accent_color=?,"
                " footer_cta=?, updated_at=? WHERE id=?",
                (fields["name"].strip(), fields.get("tagline", "").strip(), fields.get("email", "").strip(),
                 fields.get("website", "").strip(), fields.get("primary_color") or "#13294B",
                 fields.get("accent_color") or "#E8A33D", fields.get("footer_cta", "").strip()
                 or "Interested in a product? WhatsApp us for availability and pricing.", now(), company_id))
            self.db.execute("DELETE FROM addresses WHERE company_id=?", (company_id,))
            for i, a in enumerate(x for x in addresses if x.get("label", "").strip()):
                text = a.get("text", "").strip()
                self.db.execute("INSERT INTO addresses(company_id,label,text,is_placeholder,sort_order) VALUES (?,?,?,?,?)",
                                (company_id, a["label"].strip(), text, int(not text), i))
            self.db.execute("DELETE FROM contacts WHERE company_id=?", (company_id,))
            rows = [x for x in contacts if x.get("name", "").strip()]
            primary_set = any(x.get("is_primary") for x in rows)
            for i, c in enumerate(rows):
                phone = c.get("phone", "").strip()
                usable = bool(V.wa_digits(phone))
                is_primary = int(bool(c.get("is_primary")) if primary_set else (i == 0))
                self.db.execute("INSERT INTO contacts(company_id,name,phone,is_placeholder,is_primary,sort_order)"
                                " VALUES (?,?,?,?,?,?)",
                                (company_id, c["name"].strip(), V.pretty_phone(phone) if usable else phone,
                                 int(not usable), is_primary, i))

    def primary_contact(self, company_id):
        usable = self.contacts(company_id, usable_only=True)
        for c in usable:
            if c["is_primary"]:
                return c
        return usable[0] if usable else None

    # ------------------------------------------------------------ categories
    def categories(self):
        return self.q("SELECT * FROM categories ORDER BY sort_order, id")

    def category(self, key):
        col = "id" if isinstance(key, int) or str(key).isdigit() else "slug"
        return self.one(f"SELECT * FROM categories WHERE {col}=?", (key,))

    def add_category(self, name, prefix, standard="", description="", columns="size,weight_kg_m", item_label=""):
        import re
        name = name.strip()
        prefix = re.sub(r"[^A-Z0-9]", "", prefix.upper())
        if not name or not prefix:
            raise ValueError("Category name and code prefix are required.")
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if self.one("SELECT 1 FROM categories WHERE slug=? OR prefix=?", (slug, prefix)):
            raise ValueError("A category with this name or prefix already exists.")
        order = (self.one("SELECT MAX(sort_order) m FROM categories")["m"] or 0) + 10
        with self.db:
            self.db.execute("INSERT INTO categories(slug,prefix,name,item_label,short,standard,description,columns,sort_order)"
                            " VALUES (?,?,?,?,?,?,?,?,?)",
                            (slug, prefix, name, item_label.strip() or name, name, standard.strip(),
                             description.strip(), columns, order))

    # ------------------------------------------------------------ articles
    def articles(self, company_id=None, category_id=None, availability=None, search=None, flagged=False):
        sql = ("SELECT a.*, c.name AS category_name, c.slug AS category_slug, c.sort_order AS cat_order,"
               " co.name AS company_name, co.slug AS company_slug FROM articles a"
               " JOIN categories c ON c.id=a.category_id JOIN companies co ON co.id=a.company_id WHERE 1=1")
        args = []
        if company_id:
            sql += " AND a.company_id=?"; args.append(company_id)
        if category_id:
            sql += " AND a.category_id=?"; args.append(category_id)
        if availability:
            sql += " AND a.availability=?"; args.append(availability)
        if flagged:
            sql += " AND (a.check_note<>'' OR a.notes<>'')"
        if search:
            like = f"%{search.strip()}%"
            compact = f"%{search.replace(' ', '').upper()}%"
            sql += " AND (a.name LIKE ? OR a.sku LIKE ? OR a.size LIKE ? OR a.specification LIKE ?" \
                   " OR a.nominal_bore LIKE ? OR REPLACE(UPPER(a.size),' ','') LIKE ?)"
            args += [like, like, like, like, like, compact]
        sql += " ORDER BY co.id, c.sort_order, a.id"
        return self.q(sql, args)

    def article(self, article_id):
        return self.one("SELECT * FROM articles WHERE id=?", (article_id,))

    def find_by_sku(self, company_id, sku):
        return self.one("SELECT * FROM articles WHERE company_id=? AND sku=?", (company_id, sku))

    def clean_article(self, data, existing=None):
        """Normalise + validate. Returns a full field dict. Raises ValueError."""
        a = dict(existing) if existing else {}
        a.update({k: v for k, v in data.items() if k in ARTICLE_FIELDS})
        if not a.get("category_id"):
            raise ValueError("Category is required.")
        cat = self.category(int(a["category_id"]))
        if not cat:
            raise ValueError("Unknown category.")
        a["category_id"] = cat["id"]
        a["size"] = V.norm_size(a.get("size"))
        for f in ("od_mm", "thickness_mm", "weight_kg_m", "weight_kg_pc", "quantity"):
            a[f] = V.to_float(a.get(f), f)
            if a[f] is not None and a[f] < 0:
                raise ValueError(f"{f} cannot be negative.")
        for f in ("weight_kg_m", "weight_kg_pc"):
            if a[f] == 0:
                a[f] = None
        for f in ("nominal_bore", "specification", "quantity_unit", "notes", "source", "name", "sku"):
            a[f] = (a.get(f) or "").strip()
        a["pipe_class"] = (a.get("pipe_class") or "").strip().upper()
        if a["pipe_class"] not in V.PIPE_CLASSES:
            raise ValueError("Pipe class must be L, M, H or blank.")
        a["availability"] = V.norm_availability(a.get("availability"))
        if cat["slug"] == "chs" and not a["size"] and a["nominal_bore"]:
            a["size"] = a["nominal_bore"].split("(")[0].replace("mm", "NB").strip()
        if not a["size"] and not a["nominal_bore"]:
            raise ValueError("Size is required.")
        auto_name = V.make_name(cat, a)
        if not a["name"] or (existing and existing["name"] == V.make_name(cat, dict(existing))):
            a["name"] = auto_name
        if not a["sku"] or (existing and existing["sku"] == V.make_sku(cat["prefix"], existing["size"], existing["thickness_mm"])):
            a["sku"] = V.make_sku(cat["prefix"], a["size"], a["thickness_mm"])
        a["sku"] = a["sku"].upper().replace(" ", "")
        a["check_note"] = V.weight_check(cat["slug"], a)
        return a

    def save_article(self, company_id, data, article_id=None, commit=True):
        existing = self.article(article_id) if article_id else None
        if article_id and not existing:
            raise ValueError("Article not found.")
        a = self.clean_article(data, existing)
        dup = self.one("SELECT id FROM articles WHERE company_id=? AND sku=? AND id IS NOT ?",
                       (company_id, a["sku"], article_id))
        if dup:
            raise ValueError(f"Duplicate: article code {a['sku']} already exists for this company "
                             f"(id {dup['id']}). Edit that article instead.")
        ts = now()
        vals = [a[f] for f in ARTICLE_FIELDS]
        if existing:
            sets = ",".join(f"{f}=?" for f in ARTICLE_FIELDS)
            self.db.execute(f"UPDATE articles SET {sets}, check_note=?, updated_at=?, company_id=? WHERE id=?",
                            vals + [a["check_note"], ts, company_id, article_id])
            new_id = article_id
        else:
            cols = ",".join(ARTICLE_FIELDS)
            cur = self.db.execute(
                f"INSERT INTO articles({cols},check_note,company_id,created_at,updated_at)"
                f" VALUES ({','.join('?' * len(ARTICLE_FIELDS))},?,?,?,?)",
                vals + [a["check_note"], company_id, ts, ts])
            new_id = cur.lastrowid
        if commit:
            self.db.commit()
        return new_id

    def delete_article(self, article_id):
        with self.db:
            self.db.execute("DELETE FROM articles WHERE id=?", (article_id,))

    def set_availability(self, ids, availability):
        availability = V.norm_availability(availability)
        if not ids:
            return 0
        with self.db:
            cur = self.db.execute(
                f"UPDATE articles SET availability=?, updated_at=? WHERE id IN ({','.join('?' * len(ids))})",
                [availability, now()] + [int(i) for i in ids])
        return cur.rowcount

    # ------------------------------------------------------------ stats
    def stats(self, company_id):
        r = self.one(
            "SELECT COUNT(*) total,"
            " SUM(availability='available') available,"
            " SUM(availability='out_of_stock') out_of_stock,"
            " SUM(availability='unconfirmed') unconfirmed,"
            " SUM(check_note<>'' OR notes<>'') flagged"
            " FROM articles WHERE company_id=?", (company_id,))
        return {k: (r[k] or 0) for k in r.keys()}

    def last_generation(self, company_id, kind="pdf"):
        return self.one("SELECT * FROM generations WHERE company_id=? AND kind=? ORDER BY id DESC LIMIT 1",
                        (company_id, kind))

    def generations(self, limit=30):
        return self.q("SELECT g.*, c.name company_name FROM generations g JOIN companies c ON c.id=g.company_id"
                      " ORDER BY g.id DESC LIMIT ?", (limit,))

    def log_generation(self, company_id, kind, file_name, count):
        with self.db:
            self.db.execute("INSERT INTO generations(company_id,kind,file_name,article_count,created_at)"
                            " VALUES (?,?,?,?,?)", (company_id, kind, file_name, count, now()))


def open_store(path=None, seed_if_empty=True):
    s = Store(path)
    if seed_if_empty and s.is_empty():
        s.seed()
    return s


def reset_from_seed(path=None):
    path = path or os.environ.get("STOCK_DB") or DEFAULT_DB
    if os.path.exists(path):
        bk = os.path.join(os.path.dirname(path), "backups")
        os.makedirs(bk, exist_ok=True)
        shutil.copy(path, os.path.join(bk, f"inventory-{datetime.now():%Y%m%d-%H%M%S}-before-reset.db"))
        os.remove(path)
    return open_store(path)
