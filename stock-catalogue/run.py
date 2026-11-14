"""Start the Stock Manager.

  python run.py                     # start the web app on http://127.0.0.1:5000
  python run.py --generate          # generate both brochures (PDF + web) and exit
  python run.py --reset-from-seed   # rebuild the database from the screenshot data (old DB is backed up)
"""
import argparse
import os

from app import brochure_pdf, web_catalogue
from app.store import BASE_DIR, open_store, reset_from_seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--reset-from-seed", action="store_true")
    args = ap.parse_args()

    if args.reset_from_seed:
        reset_from_seed()
        print("Database rebuilt from seed data (previous database backed up in data/backups).")
        return
    if args.generate:
        store = open_store()
        out = os.environ.get("STOCK_OUTPUT") or os.path.join(BASE_DIR, "output")
        for c in store.companies():
            r = brochure_pdf.generate(store, c["slug"], out)
            print(f"{c['name']}: {r['pages']} pages, {r['articles']} articles -> {r['latest']}")
            w = web_catalogue.generate(store, c["slug"], out)
            print(f"{c['name']}: web catalogue -> {w['latest']}")
        return

    from app.web import create_app
    app = create_app()
    print(f"Stock Manager running at http://{args.host}:{args.port}  (Ctrl+C to stop)")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
