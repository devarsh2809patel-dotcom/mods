# Inventory audit: what was extracted from the screenshots

## Source pages

| # | Content | Status |
|---|---------|--------|
| 1 | Company header + Rounds/Squares, Flats, Angles | Extracted |
| 2 | Rectangular (RHS) + Square (SHS) Hollow Sections, IS 4923 ("2 of 4") | Extracted |
| 3 | Circular Hollow Sections / round pipes | Extracted |
| 4 | **Exact duplicate of screenshot 3** | Nothing new |

**Gap:** the source PDF says "2 of 4", and its header lists Channels, Beams, Plates, Sheets, TMT bars and Aluminium. None of these have tables in the screenshots, so they are **not** in the catalogue. The missing page (probably page 4) needs to be sent, or the items added with the tool (Add article > "Add a new category").

## Firms

| | C.D. Patel & Sons | Daksh Enterprise |
|---|---|---|
| Tagline | Iron and Pipe Merchant | A to Z Steel Solutions |
| Contacts | Nitin Patel +91 99250 07731, Mohit Patel +91 70484 87731 | Nitin Patel +91 99250 07731, Ujash Patel +91 98250 58831 |
| Email | cdpatelandsons@yahoo.in | dakshenterprise1@yahoo.com |
| Office | Office No. 505, Aaron Spectra, Rajpath Rangoli Road, Behind Rajpath Club, Bodakdev, Ahmedabad 380054 | same |
| Godown | Survey No. 268/1, Opp. Road Off PSP Godown, Nr. Pipe Zone, Vill. Navapura, Ta. Sanand, Dist. Ahmedabad | same |
| 3rd contact | Placeholder (not printed) | Placeholder (not printed) |

The old office address (Loha Bhavan, Nr. Old High Court, Income Tax, Ashram Road) is not stored anywhere. Automated QA checks it is absent from the PDF text, PDF metadata, raw PDF bytes and the web catalogue.

**Stock split between firms:** the screenshots are one shared section book, so nothing says which item belongs to which firm. Both firms start with the full list (442 articles each, stored as separate records). Remove what a firm does not stock with the tool.

## Articles extracted (per firm)

| Category | Articles | Columns kept |
|---|---|---|
| Rectangular Hollow Sections (IS 4923) | 62 | size, thickness, kg/m, kg/pc |
| Square Hollow Sections (IS 4923) | 72 | size, thickness, kg/m, kg/pc |
| Circular Hollow Sections / pipes (IS 1239 Pt-I / 1161 / 3601 / 3589) | 94 | NB (mm + inch), OD, thickness, L/M/H class, kg/m, kg/pc |
| Angles | 52 | size, kg/m |
| Flats | 71 | size, kg/m |
| Flats - Round Edge | 13 | size, kg/m |
| Round Bars | 39 | diameter, kg/m |
| Square Bars | 39 | side, kg/m |
| **Total** | **442** | |

Square bars come from the "sqrs." column of the Rounds table. They are separate articles because their availability can differ from round bars.

## Availability

The screenshots contain **no stock or availability information**, only reference weights. Every article starts as **UNCONFIRMED**. Nothing was assumed to be in stock.

## Values that look wrong in the source (printed as-is, flagged in the tool)

Every weight was checked against steel theory (density 7850 kg/m³) and against kg/pc = kg/m × 6 m. Open *Articles > Needs data check* in the tool to see them all. The clear errors:

| Article | Printed | Problem | Likely correct |
|---|---|---|---|
| Round bar "180" | 157.84 kg/m | 180 mm should be ~199.8 kg/m | Size is **160 mm** (160 mm = 157.8 kg/m) |
| Square bar "180" | 200.96 kg/m | same | **160 mm** (160² × 0.00785 = 200.96) |
| RHS 200×100×6.0 | 128.99 kg/pc | 26.50 × 6 = 159.00 | 159.00 |
| SHS 132×132×4.8 | 100.26 kg/pc | 18.77 × 6 = 112.62 | 112.62 |
| CHS 32 NB × 1.0 | 1.2 kg/m | theory 1.02; kg/pc 6.13 implies 1.02 | 1.02 |
| Flat 80×25 | 20.1 kg/m | theory 15.7 | 15.7 (or size is 80×32 = 20.1) |
| Flat 25×6 | 1.02 kg/m | theory 1.18 | 1.18 |
| Angle 75×75×4 | 5.5 kg/m | theory ~4.6 | size may be 75×75×5 (≈5.6) |
| SHS 25×25×2.9 | 1.86 kg/m | about 8% below theory | confirm |
| RHS 60×40×2.5 | 22.38 kg/pc | 3.62 × 6 = 21.72 | 21.72 |
| CHS 150 NB (3 rows) | kg/pc about 2% low | not × 6 m | confirm piece length |

Smaller kg/pc rounding differences (about 1-2%) are also flagged: RHS 80×40×1.4, SHS 50×50×2.9 and 3.6, CHS 25 NB × 1.0.

## Other interpretation calls

* **"ROUNDEDGE"** is a sub-heading inside the 4th Flats column. I treated the 13 rows below it (200×10 … 300×16) as round-edge flats, and they are flagged for confirmation. The 5 rows above it (75×8, 75×10, 150×20, 150×25, 180×20) are normal flats.
* **SHS 60×60** is printed split across two columns (1.6/2.0 at the bottom of one, 2.5/2.9 at the top of the next). I merged it into one size group.
* **L / M / H pipe classes** are kept exactly where printed (for example 25 NB: L = 2.5, M = 3.2, H = 4.0).
* **"40 mm 1.1½""** is a typo in the source; it is shown as 1½".
* The "sqrs." labels above the Flats tables are layout leftovers and were ignored.
* Weights are shown with 2 decimals (2.4 → 2.40). The values themselves are unchanged.
