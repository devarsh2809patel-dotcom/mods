# Stock Catalogue & Management System

> **Main tool: Stock Catalogue Studio**, a Claude artifact at https://claude.ai/artifact/Ac837AkyZGBdqMahKbqBGb
> It works in any browser, including iPad, with no install.
> * Edit articles, fields, categories, company details and colours.
> * Export PDF saves a numbered version (the PDF plus a data snapshot) that you can download or restore later.
> * Source: `artifact/stock-studio.html`. Seed data: `artifact/seed/`.
>
> The brochure PDFs in `deliverables/` come from the Studio and follow the new brand palettes. They show no availability.
> The Python/Flask tool below is the earlier version. It still shows availability and the old colours, so keep it only as an offline backup.

For **C.D. Patel & Sons** and **Daksh Enterprise**.

* A local web app to maintain both firms' stock.
* One-click generation of a separate customer PDF brochure and a searchable web catalogue for each firm.

## What you get

| Item | Where |
|---|---|
| Customer PDF brochures (current) | `deliverables/*.pdf` |
| Searchable web catalogues (single HTML file, can be shared or hosted) | `deliverables/*.html` |
| Master inventory as a spreadsheet | `deliverables/master_inventory.csv` |
| What was read from the screenshots, and what is doubtful | `docs/INVENTORY_AUDIT.md` |
| Management app source | `app/` |
| Automated QA | `qa/run_qa.py` |

## Setup (once)

You need Python 3.10 or newer (Windows, Mac or Linux).

```bash
cd stock-catalogue
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Daily use

```bash
python run.py
```

Open http://127.0.0.1:5000 in a browser.

* **Dashboard:** totals per firm, available / out of stock / to confirm, data to check, and the last brochure date.
* **Articles:** filter by firm, category, availability or search. Change availability straight from the list, or tick many rows and mark them all at once. Edit or delete (deleting asks for confirmation).
* **+ Add article:** tick one or both firms. The article code and name are generated automatically. Duplicates are blocked. You can add new categories (Channels, Beams, ...) here too.
* **Import:** download the Excel/CSV template, fill it in and upload. You see a preview first (new, updates, errors, duplicates), and nothing is saved until you confirm. When updating, blank cells keep the current value.
* **Brochures:** preview, generate the PDF and/or web catalogue for one firm or both, and download earlier versions. Every generation is kept as a dated file, plus a `..._LATEST` copy.
* **Company pages (top menu):** name, tagline, email, addresses, contact persons, WhatsApp numbers, main enquiry contact, brand colours and footer text, for each firm separately.

Command-line shortcuts:

```bash
python run.py --generate          # regenerate both firms' PDF + web catalogue
python run.py --reset-from-seed   # rebuild the database from the screenshot data (current DB is backed up first)
python qa/run_qa.py               # run all checks on freshly generated files
```

## How it works

* **Data:** `data/inventory.db` (SQLite) is the single source of truth.
  * Back it up by copying this one file.
  * The tool also saves automatic backups to `data/backups/` before every import and bulk delete.
* **Separation:** brochure design (`app/brochure_pdf.py`, `app/templates/public_catalogue.html`) only reads the data. Changing the design can never change stock records.
* **PDF:**
  * Built with ReportLab, with real embedded text, so it is searchable and copyable.
  * Clickable contents page, PDF bookmarks, and a "Contents" button on every page.
  * WhatsApp footer with every contact on every page.
  * An "Enquire" button on every article opens WhatsApp to the firm's main enquiry contact, with the article details pre-filled.
* **Web catalogue:** live search (matches `50x50` and `50 x 50`), availability filter, a contact picker that re-points all WhatsApp buttons, and a Copy button per article that copies:

  ```
  Article: SHS 50 x 50 x 2.0 mm
  Article code: SHS-50X50-2.0
  Size: 50 x 50
  Specification: IS 4923, Thickness 2.0 mm, 2.94 kg/m
  Availability: Unconfirmed
  Quantity Required:
  ```

* **Placeholders:** a contact or address without a valid value is kept in the tool, marked as a placeholder, and left out of customer brochures until filled.

## Security note

The app has no login and listens only on this computer (127.0.0.1). Do not expose it to the internet as-is. To use it from other devices on the office network, add a login first.
