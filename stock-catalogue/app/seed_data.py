"""Master inventory extracted from the uploaded section-book screenshots.

This file is the record of what was read from the source images. It is only used
to create a fresh database (python run.py --reset-from-seed). After that, the
SQLite database is the single source of truth and is edited through the tool.

Source pages:
  S1 = screenshot 1 (Rounds/Squares, Flats, Angles + company header)
  S2 = screenshot 2 (RHS + SHS, "2 of 4")
  S3 = screenshot 3 (CHS round pipes). Screenshot 4 is an exact duplicate of S3.

Rules followed:
  * Numbers are copied exactly as printed, even where they look wrong.
    Suspicious values are flagged automatically by validation.py and listed in
    docs/INVENTORY_AUDIT.md.
  * Availability is never taken from the screenshots (they contain none):
    every article starts as "unconfirmed".
"""

# ---------------------------------------------------------------- categories
# columns: which article fields the brochure / web catalogue show for the category
CATEGORIES = [
    dict(slug="rhs", prefix="RHS", name="Rectangular Hollow Sections", item_label="RHS",
         short="RHS", standard="IS 4923", sort_order=10,
         description="Rectangular steel tubes. Weight per piece is based on a 6 m length.",
         columns="size,thickness_mm,weight_kg_m,weight_kg_pc"),
    dict(slug="shs", item_label="SHS", prefix="SHS", name="Square Hollow Sections",
         short="SHS", standard="IS 4923", sort_order=20,
         description="Square steel tubes. Weight per piece is based on a 6 m length.",
         columns="size,thickness_mm,weight_kg_m,weight_kg_pc"),
    dict(slug="chs", item_label="Round Pipe", prefix="CHS", name="Circular Hollow Sections (Round Pipes)",
         short="CHS / Pipes", standard="IS 1239 (Part-I) / IS 1161 / IS 3601 / IS 3589",
         sort_order=30,
         description="Round pipes by nominal bore. L / M / H = Light / Medium / Heavy class. "
                     "Tolerance: thickness ±10%, weight ±10%.",
         columns="nominal_bore,od_mm,thickness_mm,pipe_class,weight_kg_m,weight_kg_pc"),
    dict(slug="angles", item_label="Angle", prefix="ANG", name="Angles",
         short="Angles", standard="", sort_order=40,
         description="Equal angles. Size = leg x leg x thickness (mm).",
         columns="size,weight_kg_m"),
    dict(slug="flats", item_label="Flat", prefix="FLT", name="Flats",
         short="Flats", standard="", sort_order=50,
         description="Flat bars. Size = width x thickness (mm).",
         columns="size,weight_kg_m"),
    dict(slug="flats-round-edge", item_label="Round-Edge Flat", prefix="FRE", name="Flats - Round Edge",
         short="Round-Edge Flats", standard="", sort_order=55,
         description="Round-edge flat bars. Size = width x thickness (mm).",
         columns="size,weight_kg_m"),
    dict(slug="round-bars", item_label="Round Bar", prefix="RB", name="Round Bars",
         short="Round Bars", standard="", sort_order=60,
         description="Solid round bars. Size = diameter (mm).",
         columns="size,weight_kg_m"),
    dict(slug="square-bars", item_label="Square Bar", prefix="SQB", name="Square Bars",
         short="Square Bars", standard="", sort_order=70,
         description="Solid square bars. Size = side (mm).",
         columns="size,weight_kg_m"),
]

# ---------------------------------------------------------------- companies
# The old office address (Loha Bhavan, near Old High Court, Ashram Road) is
# deliberately NOT included anywhere.
NEW_OFFICE = ("Office No. 505, Aaron Spectra, Rajpath Rangoli Road, Behind Rajpath Club, "
              "Bodakdev, Ahmedabad, Gujarat 380054, India")
GODOWN = ("Survey No. 268/1, Opp. Road Off PSP Godown, Nr. Pipe Zone, Vill. Navapura, "
          "Ta. Sanand, Dist. Ahmedabad, Gujarat, India")

COMPANIES = [
    dict(slug="cd-patel", name="C.D. Patel & Sons", tagline="Iron and Pipe Merchant",
         email="cdpatelandsons@yahoo.in", website="",
         primary_color="#13294B", accent_color="#E8A33D",
         addresses=[("Office", NEW_OFFICE, False), ("Godown", GODOWN, False)],
         contacts=[("Nitin Patel", "+91 99250 07731", False),
                   ("Mohit Patel", "+91 70484 87731", False),
                   ("Contact 3 (to be provided)", "", True)]),
    dict(slug="daksh", name="Daksh Enterprise", tagline="A to Z Steel Solutions",
         email="dakshenterprise1@yahoo.com", website="",
         primary_color="#0B4F7C", accent_color="#D9542B",
         addresses=[("Office", NEW_OFFICE, False), ("Godown", GODOWN, False)],
         contacts=[("Nitin Patel", "+91 99250 07731", False),
                   ("Ujash Patel", "+91 98250 58831", False),
                   ("Contact 3 (to be provided)", "", True)]),
]

# ---------------------------------------------------------------- raw tables
# Round / square bars, S1: size, rounds kg/m, squares kg/m
BARS = """
5 0.15 0.20|5.5 0.19 0.24|6 0.22 0.28|6.5 0.26 0.33|7 0.30 0.38|8 0.39 0.50|9 0.50 0.64
10 0.62 0.78|11 0.75 0.95|12 0.89 1.13|13 1.04 1.33|14 1.21 1.54|16 1.58 2.01|18 2.00 2.54
20 2.47 3.14|22 2.98 3.80|25 3.85 4.91|28 4.83 6.15|30 5.55 7.06|32 6.31 8.04|36 7.99 10.17
38 8.90 11.34|40 9.86 12.56|42 10.87 13.88|45 12.29 15.90|47 13.61 17.34|50 15.41 19.62
53 17.31 22.05|56 19.34 24.62|60 22.18 28.62|63 24.47 31.61|71 31.08 39.57|75 34.66 44.15
80 39.46 50.24|90 49.94 63.58|100 61.61 78.15|110 74.60 94.60|125 96.34 122.66|180 157.84 200.96
"""

# Flats, S1: "WxT kg/m"
FLATS = """
12x3 0.28|16x3 0.38|16x5 0.63|20x3 0.47|20x5 0.79|20x6 0.94|25x6 1.02|25x10 2.00|25x12 2.4
30x5 1.18|30x6 1.41|30x10 2.4|30x12 2.8|30x16 3.8|35x6 1.6|35x10 2.8|35x12 3.3|35x16 4.4
40x3 0.940|40x5 1.6|40x6 1.9|40x10 3.1|40x12 3.8|40x16 5.0|40x20 6.3|45x6 2.1|45x10 3.5
50x3 1.2|50x5 2.0|50x6 2.4|50x8 3.1|50x10 3.9|50x12 4.7|50x16 6.3|50x20 7.8|50x25 9.8
65x6 3.1|65x8 4.1|65x10 5.1|65x12 6.1|65x16 8.2|65x20 10.2|65x25 12.8|65x32 16.3|70x25 13.8
75x6 3.5|75x8 4.7|75x10 5.9|75x12 7.1|75x16 9.4|75x20 11.8|75x25 14.7|75x32 18.8|80x25 20.1
100x6 4.7|100x10 7.8|100x12 9.4|100x16 12.6|100x20 15.7|100x25 19.6|100x32 25.1
125x6 5.9|125x10 9.8|125x12 11.8|130x10 10.2|150x10 11.8|150x12 14.1|150x16 18.8
150x20 23.6|150x25 29.5|180x20 28.3
"""

# Rows printed under the "ROUNDEDGE" sub-heading, S1 (4th flats column)
FLATS_ROUND_EDGE = """
200x10 15.7|200x12 18.8|200x16 25.1|200x20 31.4|200x25 39.2|220x20 34.5
250x10 19.6|250x12 23.6|250x16 31.4|250x20 39.2|250x25 49.1|300x12 28.3|300x16 37.7
"""

# Angles, S1: "AxAxT kg/m"
ANGLES = """
20x20x3 0.900|25x25x3 1.1|25x25x5 1.8|30x30x3 1.4|30x30x5 2.2|35x35x3 1.6|35x35x5 2.6
35x35x6 3.0|40x40x3 1.8|40x40x5 3.0|40x40x6 3.5|45x45x5 3.4|45x45x6 4.0|50x50x5 3.8
50x50x6 4.5|55x55x5 4.1|55x55x6 4.9|60x60x5 4.5|60x60x6 5.4|60x60x8 7.0|65x65x6 5.8
65x65x8 7.7|65x65x10 9.4|75x75x4 5.5|75x75x6 6.8|75x75x8 8.9|75x75x10 11.0|80x80x6 7.3
80x80x8 9.6|80x80x10 11.8|90x90x6 8.2|90x90x8 10.8|90x90x10 13.4|90x90x12 15.8
100x100x6 9.2|100x100x8 12.1|100x100x10 14.9|100x100x12 17.7|110x110x8 13.4
110x110x10 16.5|110x110x12 19.6|130x130x8 15.9|130x130x10 19.7|130x130x12 23.4
130x130x15 28.9|150x150x10 22.8|150x150x12 27.2|150x150x16 35.8|150x150x18 39.9
150x150x20 44.1|200x200x16 48.5|200x200x20 60.0
"""

# RHS, S2: "size: thk kg/m kg/pc, ..."
RHS = """
40x20: 1.2 1.06 6.36, 1.4 1.22 7.34, 1.6 1.38 8.29, 1.8 1.54 9.22, 2.0 1.69 10.13, 2.5 2.05 12.29
50x25: 1.2 1.34 8.06, 1.4 1.55 9.32, 1.6 1.76 10.55, 1.8 1.96 11.77, 2.0 2.16 12.96, 2.5 2.64 15.80, 2.9 3.00 18.01
60x40: 1.2 1.81 10.88, 1.4 2.10 12.62, 1.6 2.39 14.32, 1.8 2.67 16.01, 2.0 2.94 17.67, 2.5 3.62 22.38, 2.9 4.14 24.72
66x33: 2.5 3.58 21.48, 2.9 4.09 24.42
80x40: 1.2 2.19 13.15, 1.4 2.54 15.50, 1.6 2.89 17.34, 1.8 3.23 19.40, 2.0 3.57 21.44, 2.5 4.40 26.42, 2.9 5.05 30.18, 3.2 5.53 33.18, 4.0 6.75 40.50
96x48: 1.6 3.49 20.96, 1.8 3.91 23.47, 2.0 4.33 25.96, 2.5 5.35 32.08, 2.9 6.15 36.87, 3.2 6.73 40.26, 4.0 8.26 49.32, 4.8 9.72 57.96
122x61: 2.0 5.55 33.31, 2.5 6.88 41.27, 3.6 9.71 58.02, 4.5 11.94 71.28, 5.4 14.08 84.06
145x82: 3.0 10.25 61.52, 3.5 11.88 71.25, 4.0 13.47 80.84, 4.5 15.05 90.28, 5.0 16.60 99.57, 6.0 19.62 117.71
172x92: 3.0 12.00 71.98, 3.5 13.91 83.46, 4.0 15.80 94.79, 4.5 17.66 105.97, 5.0 19.50 117.01, 6.0 23.11 138.63
200x100: 3.0 13.69 82.16, 3.5 15.89 95.33, 4.0 18.06 108.06, 4.5 20.21 121.24, 5.0 22.33 133.56, 6.0 26.50 128.99
"""

# SHS, S2. 60x60 is printed split across two columns (2 rows bottom of col 3,
# 2 rows top of col 4); merged here into one size group.
SHS = """
20x20: 1.2 0.68 4.10, 1.4 0.78 4.70, 1.6 0.88 5.27, 1.8 0.97 5.83, 2.0 1.06 6.36
25x25: 1.2 0.87 5.23, 1.4 1.00 6.01, 1.6 1.13 6.72, 1.8 1.25 7.52, 2.0 1.37 8.16, 2.5 1.66 9.93, 2.9 1.86 11.18
32x32: 1.2 1.14 6.81, 1.4 1.31 7.86, 1.6 1.48 8.89, 1.8 1.65 9.90, 2.0 1.81 10.80, 2.5 2.20 13.23, 2.9 2.50 15.00
38x38: 1.2 1.36 8.17, 1.4 1.57 9.45, 1.6 1.78 10.70, 1.8 1.99 11.93, 2.0 2.19 13.08, 2.5 2.68 16.08, 2.9 3.05 18.28
50x50: 1.2 1.81 10.88, 1.4 2.10 12.62, 1.6 2.39 14.32, 1.8 2.67 16.01, 2.0 2.94 17.67, 2.5 3.62 21.71, 2.9 4.14 24.42, 3.6 5.01 29.58
60x60: 1.6 2.89 17.34, 2.0 3.57 21.44, 2.5 4.40 26.43, 2.9 5.05 30.18
72x72: 1.6 3.49 20.96, 1.8 3.91 23.47, 2.0 4.33 25.96, 2.5 5.35 32.08, 3.0 6.34 38.05, 3.2 6.73 40.26, 4.0 8.26 49.32, 4.8 9.72 57.96
80x80: 2.0 4.78 28.70, 2.5 5.97 35.85, 2.9 6.87 41.23, 3.5 8.19 49.14, 4.0 9.26 55.60, 4.5 10.20 61.25, 5.0 11.33 68.00
91.5x91.5: 3.0 8.13 48.78, 3.5 9.54 58.02, 4.0 10.65 63.88, 4.5 11.93 71.28, 5.0 13.08 78.39, 5.4 14.08 84.06
100x100: 2.0 6.18 37.10, 2.5 7.55 45.27, 2.9 8.85 53.10, 3.2 10.0 60.00, 4.0 12.16 73.00, 5.0 15.08 90.50, 6.0 18.00 108.00
113.5x113.5: 4.8 15.92 95.52, 5.4 17.81 106.44
132x132: 4.8 18.77 100.26, 5.4 20.95 125.28
150x150: 4.0 18.01 108.06, 5.0 22.32 133.56
"""

# CHS, S3: "NB|inch|OD: thk kg/m kg/pc [class], ..."
CHS = """
15|½"|21.3: 1.2 0.59 3.57, 1.4 0.69 4.12, 1.6 0.78 4.66, 1.8 0.87 5.19, 2.0 0.95 5.71 L, 2.6 1.20 7.26 M, 3.2 1.42 8.59 H
20|¾"|26.9: 1.2 0.76 4.56, 1.4 0.88 5.28, 1.6 1.00 5.99, 1.8 1.11 6.69, 2.0 1.23 7.37, 2.3 1.39 8.28 L, 2.6 1.56 9.36 M, 3.2 1.87 11.22 H
25|1"|33.7: 1.0 0.84 4.84, 1.2 0.96 5.77, 1.4 1.12 6.69, 1.6 1.27 7.62, 1.8 1.42 8.52, 2.0 1.56 9.38, 2.5 1.92 11.54 L, 3.2 2.41 14.46 M, 4.0 2.93 17.58 H
32|1¼"|42.4: 1.0 1.2 6.13, 1.2 1.22 7.32, 1.4 1.42 8.49, 1.6 1.61 9.66, 1.8 1.80 10.81, 2.0 1.99 11.96, 2.5 2.46 14.76 L, 3.2 3.10 18.60 M, 4.0 3.79 22.74 H
40|1½"|48.3: 1.2 1.39 8.36, 1.4 1.62 9.72, 1.6 1.84 11.06, 1.8 2.06 12.39, 2.0 2.28 13.70, 2.5 2.82 16.94, 2.9 3.25 19.38 L, 3.2 3.56 21.36 M, 4.0 4.37 26.22 H
50|2"|60.3: 1.2 1.75 10.50, 1.4 2.03 12.20, 1.6 2.32 13.92, 1.8 2.60 15.58, 2.0 2.88 17.25, 2.5 3.56 21.38, 2.9 4.10 24.48 L, 3.6 5.03 30.20 M, 4.5 6.19 37.15 H
65|2½"|76.1: 1.4 2.58 15.47, 1.6 2.94 17.64, 1.8 3.30 19.79, 2.0 3.66 21.93, 2.5 4.54 27.23, 3.2 5.75 34.26 L, 3.6 6.44 38.52 M, 4.5 7.94 47.58 H
80|3"|88.9: 1.6 3.45 20.67, 1.8 3.87 23.20, 2.0 4.29 25.72, 2.5 5.33 31.96, 3.2 6.76 40.32 L, 4.0 8.37 50.16 M, 4.8 9.95 59.40 H
100|4"|114.3: 1.6 4.45 26.68, 1.8 4.99 29.96, 2.0 5.54 33.23, 3.6 9.82 58.52 L, 4.5 12.20 73.20 M, 5.4 14.50 87.01 H
125|5"|139.7: 4.5 15.00 90.02, 4.8 15.96 95.40 M, 5.4 17.90 107.40 H
150|6"|168.3: 4.5 18.18 106.80, 4.8 19.35 113.40 M, 5.4 21.69 127.80 H
200|8"|219.1: 4.3 22.72 136.67, 4.8 25.40 152.40, 5.0 26.38 158.28, 5.6 29.50 177.00, 5.9 31.00 186.00, 8.0 41.65 249.89
250|10"|273: 4.3 28.49 170.94, 5.0 33.04 198.24, 5.4 35.63 213.78, 6.0 39.50 237.04, 8.0 52.28 313.69
300|12"|323.9: 5.0 39.32 235.92, 5.4 42.41 254.48, 6.0 47.03 282.18, 6.3 49.30 295.18, 8.0 62.32 373.94
"""

# Source-reading notes attached to specific articles (beyond automatic weight checks).
SOURCE_NOTES = {
    ("round-bars", "180"): "Printed size 180 mm, but both weights match a 160 mm bar. Confirm size.",
    ("square-bars", "180"): "Printed size 180 mm, but both weights match a 160 mm bar. Confirm size.",
    ("chs", "32-1.0"): "Kg/m printed as '1.2'; Kg/pc 6.13 implies 1.02 kg/m. Confirm.",
}
SOURCE_NOTE_GROUP = {
    "flats-round-edge": "Source prints these under a 'ROUNDEDGE' sub-heading. Confirm these are round-edge flats.",
}


def _f(s):
    return float(s)


def _fmt_num(x):
    return ("%g" % x)


def build_articles():
    """Return the seed article list (without company), in source order."""
    out = []

    rows = [r.split() for r in BARS.replace("\n", "|").split("|") if r.strip()]
    for size, rnd, sq in rows:
        out.append(dict(category="round-bars", size=size, weight_kg_m=_f(rnd),
                        source="S1 Rounds"))
    for size, rnd, sq in rows:
        out.append(dict(category="square-bars", size=size, weight_kg_m=_f(sq),
                        source="S1 Rounds (sqrs. column)"))

    for cat, block, src in (("flats", FLATS, "S1 Flats"),
                            ("flats-round-edge", FLATS_ROUND_EDGE, "S1 Flats (ROUNDEDGE)"),
                            ("angles", ANGLES, "S1 Angles")):
        for r in block.replace("\n", "|").split("|"):
            if not r.strip():
                continue
            size, w = r.split()
            out.append(dict(category=cat, size=size.replace("x", " x "), weight_kg_m=_f(w),
                            source=src))

    for cat, block, src in (("rhs", RHS, "S2 RHS IS 4923"), ("shs", SHS, "S2 SHS IS 4923")):
        for line in block.strip().splitlines():
            size, rest = line.split(":")
            for item in rest.split(","):
                t, kgm, kgpc = item.split()
                out.append(dict(category=cat, size=size.strip().replace("x", " x "),
                                thickness_mm=_f(t), weight_kg_m=_f(kgm), weight_kg_pc=_f(kgpc),
                                source=src))

    for line in CHS.strip().splitlines():
        head, rest = line.split(":")
        nb, inch, od = head.split("|")
        for item in rest.split(","):
            parts = item.split()
            t, kgm, kgpc = parts[:3]
            cls = parts[3] if len(parts) > 3 else ""
            out.append(dict(category="chs", size=f"{nb} NB", nominal_bore=f"{nb} mm ({inch})",
                            od_mm=_f(od), thickness_mm=_f(t), weight_kg_m=_f(kgm),
                            weight_kg_pc=_f(kgpc), pipe_class=cls, source="S3 CHS"))

    # attach manual source notes
    for a in out:
        notes = []
        if a["category"] in SOURCE_NOTE_GROUP:
            notes.append(SOURCE_NOTE_GROUP[a["category"]])
        key = (a["category"], a["size"])
        if key in SOURCE_NOTES:
            notes.append(SOURCE_NOTES[key])
        if a["category"] == "chs":
            nb = a["size"].split()[0]
            k2 = ("chs", f"{nb}-{_fmt_num(a['thickness_mm'])}")
            if k2 in SOURCE_NOTES:
                notes.append(SOURCE_NOTES[k2])
            if ("chs", nb) in SOURCE_NOTES:
                notes.append(SOURCE_NOTES[("chs", nb)])
        a["notes"] = " ".join(notes)
        a["availability"] = "unconfirmed"
    return out
