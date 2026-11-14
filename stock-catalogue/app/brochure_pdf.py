"""Renders a company's stock catalogue to PDF (ReportLab).

* Real text everywhere (searchable, selectable, copyable).
* Clickable contents page, PDF bookmarks, "Contents" button in every page header.
* WhatsApp enquiry footer with every usable contact on every page.
* Per-article "Enquire" button opening WhatsApp with the article pre-filled.
Two render passes: the first measures section page numbers, the second prints them.
"""
import io
import os
import shutil

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, FrameBreak, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

from . import catalogue

PAGE_W, PAGE_H = A4
MARGIN = 36
HEADER_H = 50
FOOTER_H = 72
CONTENT_W = PAGE_W - 2 * MARGIN
SECTION_HEAD_H = 74
GUTTER = 16

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
F, FB, FI = "Carlito", "Carlito-Bold", "Carlito-Italic"

GREEN = colors.HexColor("#1E8E3E")
WA_GREEN = colors.HexColor("#1DA851")
RED = colors.HexColor("#C62828")
GREY_BG = colors.HexColor("#E7E9ED")
GREY_TX = colors.HexColor("#4A5058")
INK = colors.HexColor("#1F242B")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#D9DDE3")

STATUS_STYLE = {
    "available": (GREEN, colors.white),
    "out_of_stock": (RED, colors.white),
    "unconfirmed": (GREY_BG, GREY_TX),
}

TWO_COLUMN_MAX_COLS = 2   # sections with <= this many data columns use the 2-column layout

_fonts_done = False


def register_fonts():
    global _fonts_done
    if _fonts_done:
        return
    pdfmetrics.registerFont(TTFont(F, os.path.join(FONT_DIR, "Carlito-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FB, os.path.join(FONT_DIR, "Carlito-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(FI, os.path.join(FONT_DIR, "Carlito-Italic.ttf")))
    addMapping(F, 0, 0, F); addMapping(F, 1, 0, FB); addMapping(F, 0, 1, FI); addMapping(F, 1, 1, FB)
    _fonts_done = True


def tint(c, f):
    """Mix colour c with white; f=0 -> c, f=1 -> white."""
    return colors.Color(c.red + (1 - c.red) * f, c.green + (1 - c.green) * f, c.blue + (1 - c.blue) * f)


def sw(text, font, size):
    return pdfmetrics.stringWidth(text, font, size)


# ------------------------------------------------------------------ drawing helpers
def chat_icon(c, cx, cy, r, bg=WA_GREEN, fg=colors.white):
    c.saveState()
    c.setFillColor(bg); c.circle(cx, cy, r, stroke=0, fill=1)
    c.setFillColor(fg)
    c.roundRect(cx - r * 0.55, cy - r * 0.32, r * 1.1, r * 0.78, r * 0.25, stroke=0, fill=1)
    p = c.beginPath(); p.moveTo(cx - r * 0.38, cy - r * 0.28); p.lineTo(cx - r * 0.5, cy - r * 0.62)
    p.lineTo(cx - r * 0.08, cy - r * 0.28); p.close(); c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(bg)
    for dx in (-0.27, 0, 0.27):
        c.circle(cx + dx * r, cy + r * 0.07, r * 0.08, stroke=0, fill=1)
    c.restoreState()


def search_icon(c, cx, cy, r, col):
    c.saveState(); c.setStrokeColor(col); c.setLineWidth(r * 0.28)
    c.circle(cx - r * 0.15, cy + r * 0.15, r * 0.55, stroke=1, fill=0)
    c.line(cx + r * 0.25, cy - r * 0.25, cx + r * 0.75, cy - r * 0.75)
    c.restoreState()


def pill(c, x, y, w, h, status, label, size=6.4):
    bg, fg = STATUS_STYLE[status]
    c.saveState(); c.setFillColor(bg); c.roundRect(x, y, w, h, h / 2, stroke=0, fill=1)
    c.setFillColor(fg); c.setFont(FB, size)
    c.drawCentredString(x + w / 2, y + (h - size * 0.7) / 2, label)
    c.restoreState()


def button(c, x, y, w, h, label, url, bg=WA_GREEN, fg=colors.white, size=8.5, icon=True):
    c.saveState(); c.setFillColor(bg); c.roundRect(x, y, w, h, h / 2, stroke=0, fill=1)
    tx = x + w / 2
    if icon:
        chat_icon(c, x + h / 2 + 1, y + h / 2, h * 0.36, bg=fg, fg=bg)
        tx = x + h / 2 + (w - h / 2) / 2 + 1
    c.setFillColor(fg); c.setFont(FB, size)
    c.drawCentredString(tx, y + (h - size * 0.7) / 2, label)
    c.restoreState()
    if url:
        c.linkURL(url, (x, y, x + w, y + h), relative=0, thickness=0)


# ------------------------------------------------------------------ flowables
class StatusPill(Flowable):
    def __init__(self, status, label, w, h=10.5):
        super().__init__(); self.status, self.label, self.w, self.h = status, label, w, h

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        pill(self.canv, 0, 0, self.w, self.h, self.status, self.label, 6.2 if self.w < 60 else 6.6)


class EnquireButton(Flowable):
    def __init__(self, url, w, h=11, label="Enquire"):
        super().__init__(); self.url, self.w, self.h, self.label = url, w, h, label

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c = self.canv
        c.saveState(); c.setFillColor(WA_GREEN)
        c.roundRect(0, 0, self.w, self.h, self.h / 2, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont(FB, 6.6)
        c.drawCentredString(self.w / 2, (self.h - 6.6 * 0.7) / 2, self.label)
        c.restoreState()
        c.linkURL(self.url, (0, 0, self.w, self.h), relative=1, thickness=0)


class SectionHeader(Flowable):
    def __init__(self, sec, number, brand, width):
        super().__init__()
        self.sec, self.number, self.brand, self.width = sec, number, brand, width
        self.key, self.title = sec["key"], sec["title"]

    def wrap(self, aw, ah):
        return self.width, SECTION_HEAD_H - 8

    def draw(self):
        c, s, b = self.canv, self.sec, self.brand
        c.bookmarkPage(self.key)
        c.addOutlineEntry(f"{self.number:02d}  {self.title}", self.key, level=0)
        top = SECTION_HEAD_H - 8
        c.setFillColor(b["accent"]); c.rect(0, 6, 4, top - 8, stroke=0, fill=1)
        c.setFont(FB, 8); c.setFillColor(b["accent"])
        c.drawString(14, top - 12, f"SECTION {self.number:02d}")
        c.setFont(FB, 21); c.setFillColor(b["primary"])
        c.drawString(14, top - 34, self.title)
        meta = []
        if s["standard"]:
            meta.append(s["standard"])
        meta.append(f"{len(s['rows'])} articles")
        c.setFont(F, 8.8); c.setFillColor(MUTED)
        c.drawString(14, top - 48, "  ·  ".join(meta))
        if s["description"]:
            c.drawString(14, top - 59, s["description"][:150])
        # availability summary (right)
        x = self.width
        for key in ("unconfirmed", "out_of_stock", "available"):
            n = s["counts"][key]
            label = f"{catalogue.STATUS_LABEL[key]}  {n}"
            w = sw(label, FB, 6.4) + 12
            x -= w
            pill(c, x, top - 14, w, 11, key, label)
            x -= 5


class TOCRow(Flowable):
    H = 34

    def __init__(self, number, sec, page, brand, width):
        super().__init__()
        self.number, self.sec, self.page, self.brand, self.width = number, sec, page, brand, width

    def wrap(self, aw, ah):
        return self.width, self.H

    def draw(self):
        c, b, s = self.canv, self.brand, self.sec
        c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(0, 0, self.width, 0)
        c.setFillColor(b["primary"]); c.roundRect(0, 7, 22, 20, 4, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont(FB, 10); c.drawCentredString(11, 13.5, f"{self.number:02d}")
        c.setFillColor(INK); c.setFont(FB, 12.5); c.drawString(32, 18, s["title"])
        sub = "  ·  ".join(x for x in (s["standard"], f"{len(s['rows'])} articles") if x)
        c.setFillColor(MUTED); c.setFont(F, 8.5); c.drawString(32, 7, sub)
        page = str(self.page) if self.page else "-"
        c.setFillColor(b["primary"]); c.setFont(FB, 12.5)
        c.drawRightString(self.width - 4, 13, page)
        c.setFont(F, 8); c.setFillColor(MUTED)
        c.drawRightString(self.width - 26, 13, "page")
        c.linkRect("", self.sec["key"], (0, 0, self.width, self.H), relative=1, thickness=0)


class InfoBoxes(Flowable):
    """Search tips + availability legend + notes, on the contents page."""
    H = 150

    def __init__(self, ctx, brand, width):
        super().__init__(); self.ctx, self.brand, self.width = ctx, brand, width

    def wrap(self, aw, ah):
        return self.width, self.H

    def draw(self):
        c, b = self.canv, self.brand
        bw = (self.width - 2 * 12) / 3
        boxes = [
            ("Search this catalogue", [
                "Press Ctrl+F (Windows) or Cmd+F (Mac), or tap the search icon in your PDF app.",
                "Type a size such as 50x50, 40 x 20, 25 NB or an article code such as SHS-50X50-2.0."]),
            ("Availability", None),
            ("Enquire on WhatsApp", [
                "Tap Enquire next to any article. WhatsApp opens with the article details already filled in.",
                "Add the quantity you need and press send."]),
        ]
        for i, (title, lines) in enumerate(boxes):
            x = i * (bw + 12)
            c.setFillColor(tint(b["primary"], 0.93)); c.roundRect(x, 0, bw, self.H, 8, stroke=0, fill=1)
            if i == 0:
                search_icon(c, x + 18, self.H - 20, 7, b["primary"])
            elif i == 2:
                chat_icon(c, x + 18, self.H - 20, 8)
            else:
                c.setFillColor(GREEN); c.circle(x + 18, self.H - 20, 7, stroke=0, fill=1)
            c.setFillColor(b["primary"]); c.setFont(FB, 11); c.drawString(x + 32, self.H - 24, title)
            if lines:
                y = self.H - 42
                for ln in lines:
                    p = Paragraph(ln, ParagraphStyle("t", fontName=F, fontSize=8.8, leading=11.5, textColor=INK))
                    _, h = p.wrap(bw - 26, 200)
                    p.drawOn(c, x + 13, y - h); y -= h + 6
            else:
                y = self.H - 48
                for key, desc in (("available", "In stock now."),
                                  ("out_of_stock", "Not in stock at present."),
                                  ("unconfirmed", "Not yet confirmed - ask us.")):
                    pill(c, x + 13, y - 2, 62, 12, key, catalogue.STATUS_LABEL[key])
                    c.setFillColor(INK); c.setFont(F, 8.6); c.drawString(x + 82, y + 1, desc)
                    y -= 22
                c.setFillColor(MUTED); c.setFont(FI, 7.6)
                c.drawString(x + 13, y - 4, f"Stock position as on {self.ctx['generated_label']}.")


# ------------------------------------------------------------------ document
class CatalogueDoc(BaseDocTemplate):
    def __init__(self, buf, ctx, brand, total_pages, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=HEADER_H, bottomMargin=FOOTER_H, **kw)
        self.ctx, self.brand, self.total_pages = ctx, brand, total_pages
        self.section_pages, self.current_section = {}, ""
        top = PAGE_H - HEADER_H - 8
        bottom = FOOTER_H + 10
        h = top - bottom
        col_w = (CONTENT_W - GUTTER) / 2
        one = Frame(MARGIN, bottom, CONTENT_W, h, id="main", leftPadding=0, rightPadding=0,
                    topPadding=0, bottomPadding=0)
        head = Frame(MARGIN, top - SECTION_HEAD_H, CONTENT_W, SECTION_HEAD_H, id="head",
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        l1 = Frame(MARGIN, bottom, col_w, h - SECTION_HEAD_H, id="l1", leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0)
        r1 = Frame(MARGIN + col_w + GUTTER, bottom, col_w, h - SECTION_HEAD_H, id="r1",
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        l2 = Frame(MARGIN, bottom, col_w, h, id="l2", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        r2 = Frame(MARGIN + col_w + GUTTER, bottom, col_w, h, id="r2", leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0)
        cover = Frame(MARGIN, bottom, CONTENT_W, 20, id="cover")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[cover], onPageEnd=self.draw_cover),
            PageTemplate(id="one", frames=[one], onPageEnd=self.draw_chrome),
            PageTemplate(id="two_first", frames=[head, l1, r1], onPageEnd=self.draw_chrome,
                         autoNextPageTemplate="two"),
            PageTemplate(id="two", frames=[l2, r2], onPageEnd=self.draw_chrome),
        ])
        co = ctx["company"]
        self.title = f"{co['name']} - Stock Catalogue"
        self.author = co["name"]
        self.subject = f"Stock catalogue, {ctx['generated_label']}"
        self.keywords = ", ".join(s["title"] for s in ctx["sections"])
        self.creator = "Stock Catalogue Manager"

    def afterFlowable(self, f):
        if isinstance(f, SectionHeader):
            self.section_pages[f.key] = self.page
            self.current_section = f.title
        elif getattr(f, "_toc_anchor", False):
            self.current_section = "Contents"

    # ---- page chrome
    def draw_footer(self, c):
        ctx, b = self.ctx, self.brand
        c.saveState()
        c.setFillColor(tint(b["primary"], 0.94)); c.rect(0, 0, PAGE_W, FOOTER_H, stroke=0, fill=1)
        c.setFillColor(b["accent"]); c.rect(0, FOOTER_H - 2.5, PAGE_W, 2.5, stroke=0, fill=1)
        chat_icon(c, MARGIN + 8, FOOTER_H - 20, 8)
        c.setFillColor(b["primary"]); c.setFont(FB, 10.5)
        c.drawString(MARGIN + 22, FOOTER_H - 24, ctx["company"]["footer_cta"])
        c.setFillColor(MUTED); c.setFont(F, 8.5)
        total = self.total_pages or "-"
        c.drawRightString(PAGE_W - MARGIN, FOOTER_H - 24, f"Page {self.page} of {total}")
        x, y, h = MARGIN, 14, 22
        for ct in ctx["contacts"]:
            label = f"{ct['name']}  {ct['phone']}"
            w = sw(label, FB, 8.6) + h + 12
            button(c, x, y, w, h, label, ct["wa"], size=8.6)
            x += w + 8
        if ctx["company"]["email"] and x + sw(ctx["company"]["email"], F, 8.5) < PAGE_W - MARGIN:
            c.setFillColor(MUTED); c.setFont(F, 8.5)
            c.drawRightString(PAGE_W - MARGIN, y + 7.5, ctx["company"]["email"])
            c.linkURL(f"mailto:{ctx['company']['email']}",
                      (PAGE_W - MARGIN - sw(ctx["company"]["email"], F, 8.5), y, PAGE_W - MARGIN, y + h),
                      relative=0, thickness=0)
        c.restoreState()

    def draw_chrome(self, c, doc):
        b, co = self.brand, self.ctx["company"]
        c.saveState()
        c.setFillColor(b["primary"]); c.rect(0, PAGE_H - 5, PAGE_W, 5, stroke=0, fill=1)
        y = PAGE_H - 30
        c.setFillColor(b["primary"]); c.setFont(FB, 12); c.drawString(MARGIN, y, co["name"])
        c.setFillColor(MUTED); c.setFont(F, 9)
        c.drawString(MARGIN + sw(co["name"], FB, 12) + 8, y, co["tagline"])
        # contents button
        bw, bh = 68, 17
        bx, by = PAGE_W - MARGIN - bw, y - 5
        c.setStrokeColor(b["primary"]); c.setLineWidth(0.8); c.setFillColor(colors.white)
        c.roundRect(bx, by, bw, bh, bh / 2, stroke=1, fill=1)
        c.setFillColor(b["primary"]); c.setFont(FB, 8.2)
        c.drawCentredString(bx + bw / 2, by + 5.3, "‹  Contents")
        c.linkRect("", "contents", (bx, by, bx + bw, by + bh), relative=0, thickness=0)
        if self.current_section and self.current_section != "Contents":
            c.setFillColor(GREY_TX); c.setFont(FB, 9)
            c.drawRightString(bx - 12, y, self.current_section)
        c.setStrokeColor(LINE); c.setLineWidth(0.7); c.line(MARGIN, PAGE_H - HEADER_H + 6, PAGE_W - MARGIN, PAGE_H - HEADER_H + 6)
        c.restoreState()
        self.draw_footer(c)

    def draw_cover(self, c, doc):
        ctx, b, co = self.ctx, self.brand, self.ctx["company"]
        c.bookmarkPage("cover"); c.addOutlineEntry("Cover & contacts", "cover", level=0)
        block_h = 372
        y0 = PAGE_H - block_h
        c.saveState()
        c.setFillColor(b["primary"]); c.rect(0, y0, PAGE_W, block_h, stroke=0, fill=1)
        # decorative section profiles (hollow squares / rectangles / circles)
        c.setStrokeColor(tint(b["primary"], 0.82)); c.setLineWidth(1.2)
        c.setStrokeAlpha(0.35)
        gx, gy = PAGE_W - 210, y0 + 70
        for r in range(4):
            for k in range(4):
                x, y = gx + k * 46, gy + r * 62
                if (r + k) % 3 == 0:
                    c.circle(x + 18, y + 18, 18, stroke=1, fill=0); c.circle(x + 18, y + 18, 13, stroke=1, fill=0)
                elif (r + k) % 3 == 1:
                    c.rect(x, y, 36, 36, stroke=1, fill=0); c.rect(x + 5, y + 5, 26, 26, stroke=1, fill=0)
                else:
                    c.rect(x, y + 8, 36, 20, stroke=1, fill=0); c.rect(x + 4, y + 12, 28, 12, stroke=1, fill=0)
        c.setStrokeAlpha(1)
        c.setFillColor(b["accent"]); c.rect(0, y0, PAGE_W, 6, stroke=0, fill=1)
        c.setFillColor(b["accent"]); c.setFont(FB, 10)
        c.drawString(MARGIN + 4, PAGE_H - 70, "S T O C K   C A T A L O G U E")
        name_size = 40 if sw(co["name"], FB, 40) < 330 else 30
        c.setFillColor(colors.white); c.setFont(FB, name_size)
        c.drawString(MARGIN + 2, PAGE_H - 116, co["name"])
        c.setFillColor(b["accent"]); c.setFont(FB, 16)
        c.drawString(MARGIN + 3, PAGE_H - 140, co["tagline"])
        c.setFillColor(tint(b["primary"], 0.75)); c.setFont(F, 10.5)
        c.drawString(MARGIN + 3, PAGE_H - 164, f"Stock position as on {ctx['generated_label']}")
        # product range chips
        c.setFont(FB, 9)
        x, y = MARGIN + 3, PAGE_H - 210
        c.setFillColor(tint(b["primary"], 0.6)); c.setFont(FB, 8)
        c.drawString(x, y + 22, "PRODUCT RANGE")
        for s in ctx["sections"]:
            label = s["short"]
            w = sw(label, FB, 9) + 18
            if x + w > PAGE_W - 230:
                x, y = MARGIN + 3, y - 24
            c.setStrokeColor(colors.white); c.setStrokeAlpha(0.6); c.setLineWidth(0.8)
            c.roundRect(x, y - 4, w, 17, 8.5, stroke=1, fill=0); c.setStrokeAlpha(1)
            c.setFillColor(colors.white); c.setFont(FB, 9); c.drawCentredString(x + w / 2, y + 1.5, label)
            c.linkRect("", s["key"], (x, y - 4, x + w, y + 13), relative=0, thickness=0)
            x += w + 7
        c.setFillColor(colors.white); c.setFont(FB, 22)
        c.drawString(MARGIN + 3, y0 + 34, f"{ctx['total']}")
        c.setFont(F, 10); c.setFillColor(tint(b["primary"], 0.7))
        c.drawString(MARGIN + 6 + sw(str(ctx['total']), FB, 22), y0 + 35,
                     f"articles in {len(ctx['sections'])} categories")
        c.restoreState()

        # ---- how to use
        y = y0 - 40
        c.setFillColor(b["primary"]); c.setFont(FB, 14); c.drawString(MARGIN, y, "How to use this catalogue")
        steps = [
            ("1", "Find", "Use Ctrl+F / Cmd+F or the search icon in your PDF app. Type a size such as "
                          "50x50, 40 x 20 or 25 NB."),
            ("2", "Check availability", "Every article shows a status: Available, Out of stock or "
                                        "Unconfirmed (ask us)."),
            ("3", "Enquire on WhatsApp", "Tap Enquire next to an article. WhatsApp opens with the "
                                         "details filled in. Add your quantity and send."),
        ]
        sw3 = (CONTENT_W - 24) / 3
        for i, (n, t, d) in enumerate(steps):
            x = MARGIN + i * (sw3 + 12)
            c.setFillColor(b["accent"]); c.circle(x + 11, y - 26, 11, stroke=0, fill=1)
            c.setFillColor(colors.white); c.setFont(FB, 11); c.drawCentredString(x + 11, y - 30, n)
            c.setFillColor(INK); c.setFont(FB, 11); c.drawString(x + 28, y - 30, t)
            p = Paragraph(d, ParagraphStyle("s", fontName=F, fontSize=9, leading=11.8, textColor=GREY_TX))
            _, h = p.wrap(sw3 - 28, 100); p.drawOn(c, x + 28, y - 38 - h)
        # ---- contacts
        y -= 108
        c.setFillColor(b["primary"]); c.setFont(FB, 14); c.drawString(MARGIN, y, "Talk to us")
        n = len(ctx["contacts"])
        cw = (CONTENT_W - (n - 1) * 12) / max(n, 1)
        for i, ct in enumerate(ctx["contacts"]):
            x = MARGIN + i * (cw + 12)
            top = y - 12
            c.setFillColor(tint(b["primary"], 0.93)); c.roundRect(x, top - 78, cw, 78, 8, stroke=0, fill=1)
            c.setFillColor(INK); c.setFont(FB, 13); c.drawString(x + 14, top - 22, ct["name"])
            c.setFillColor(GREY_TX); c.setFont(F, 11); c.drawString(x + 14, top - 38, ct["phone"])
            bw = min(96, (cw - 38) * 0.6)
            button(c, x + 14, top - 66, bw, 20, "WhatsApp", ct["wa"], size=9)
            cbw = 52
            c.setStrokeColor(b["primary"]); c.setLineWidth(0.9); c.setFillColor(colors.white)
            c.roundRect(x + 22 + bw, top - 66, cbw, 20, 10, stroke=1, fill=1)
            c.setFillColor(b["primary"]); c.setFont(FB, 9)
            c.drawCentredString(x + 22 + bw + cbw / 2, top - 59.5, "Call")
            c.linkURL(ct["tel"], (x + 22 + bw, top - 66, x + 22 + bw + cbw, top - 46), relative=0, thickness=0)
        # ---- addresses
        y -= 118
        cols = list(ctx["addresses"])
        if co["email"]:
            cols.append({"label": "Email", "text": co["email"]})
        if co["website"]:
            cols.append({"label": "Website", "text": co["website"]})
        if cols:
            aw = (CONTENT_W - (len(cols) - 1) * 16) / len(cols)
            for i, a in enumerate(cols):
                x = MARGIN + i * (aw + 16)
                c.setFillColor(b["accent"]); c.rect(x, y - 2, 3, 14, stroke=0, fill=1)
                c.setFillColor(b["primary"]); c.setFont(FB, 10.5); c.drawString(x + 9, y, a["label"])
                p = Paragraph(a["text"], ParagraphStyle("a", fontName=F, fontSize=9, leading=11.5, textColor=INK))
                _, h = p.wrap(aw - 9, 90); p.drawOn(c, x + 9, y - 8 - h)
                if a["label"] == "Email":
                    c.linkURL(f"mailto:{a['text']}", (x, y - 8 - h, x + aw, y + 12), relative=0, thickness=0)
        self.draw_footer(c)


def _brand(company):
    return {"primary": colors.HexColor(company["primary_color"]),
            "accent": colors.HexColor(company["accent_color"])}


def _table(sec, brand, width, compact):
    cols = sec["columns"]
    fs = 7.6 if compact else 8.6
    if compact:
        status_w, enq_w = 58, 40
    else:
        status_w, enq_w = 74, 50
    code_w = 70 if compact else (88 if len(cols) > 4 else 100)
    pad = 1.9 if compact else 2.6
    btn_h = 9.6 if compact else 11
    rest = width - status_w - enq_w - code_w
    # proportional data columns (size wider)
    weights = [1.6 if c in ("size", "nominal_bore") else 1.0 for c in cols]
    data_w = [rest * w / sum(weights) for w in weights]
    col_w = [code_w] + data_w + [status_w, enq_w]
    header = ["Article code"] + sec["column_titles"] + ["Availability", ""]
    rows = [header]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), brand["primary"]),
        ("FONTNAME", (0, 1), (-1, -1), F), ("FONTSIZE", (0, 1), (-1, -1), fs),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), FB), ("FONTSIZE", (0, 0), (-1, 0), fs - 0.3),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TEXTCOLOR", (0, 1), (0, -1), GREY_TX),
        ("FONTSIZE", (0, 1), (0, -1), fs - 0.8),
    ]
    num_cols = {"weight_kg_m", "weight_kg_pc", "thickness_mm", "od_mm"}
    for j, c in enumerate(cols, start=1):
        if c in num_cols:
            style.append(("ALIGN", (j, 0), (j, -1), "RIGHT"))
        if c in ("size", "nominal_bore"):
            style.append(("FONTNAME", (j, 1), (j, -1), FB))
        if c == "pipe_class":
            style.append(("ALIGN", (j, 0), (j, -1), "CENTER"))
    band_bg = tint(brand["primary"], 0.95)
    for i, it in enumerate(sec["rows"], start=1):
        row = [it["sku"]]
        for c in cols:
            row.append(it["cells"][c])
        row.append(StatusPill(it["availability"], it["status"], status_w - 8, btn_h))
        row.append(EnquireButton(it["wa"], enq_w - 8, btn_h))
        rows.append(row)
        if it["band"]:
            style.append(("BACKGROUND", (0, i), (-1, i), band_bg))
        if it["first_in_group"] and i > 1:
            style.append(("LINEABOVE", (0, i), (-1, i), 0.6, LINE))
        elif not it["first_in_group"]:
            for j, c in enumerate(cols, start=1):
                if c in ("size", "nominal_bore", "od_mm"):
                    style.append(("TEXTCOLOR", (j, i), (j, i), colors.HexColor("#A3A9B1")))
                    style.append(("FONTNAME", (j, i), (j, i), F))
    style += [("FONTNAME", (0, 0), (-1, 0), FB), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    t = Table(rows, colWidths=col_w, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle(style))
    return t


class _Anchor(Flowable):
    """Zero-size flowable that registers a named destination."""
    def __init__(self, key, title):
        super().__init__(); self.key, self.title = key, title
        self._toc_anchor = key == "contents"

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=0)


def _story(ctx, brand, section_pages):
    story = [Spacer(1, 1), NextPageTemplate("one"), PageBreak()]
    story.append(_Anchor("contents", "Contents"))
    story.append(Paragraph("Contents", ParagraphStyle("c", fontName=FB, fontSize=26, leading=30,
                                                      textColor=brand["primary"])))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Tap a section to jump to it. Every page has a <b>Contents</b> button at the top "
                           "to bring you back here.",
                           ParagraphStyle("c2", fontName=F, fontSize=10, leading=13, textColor=MUTED)))
    story.append(Spacer(1, 14))
    for i, s in enumerate(ctx["sections"], start=1):
        story.append(TOCRow(i, s, section_pages.get(s["key"]), brand, CONTENT_W))
    story.append(Spacer(1, 22))
    story.append(InfoBoxes(ctx, brand, CONTENT_W))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Notes: weights are as per standard section tables and are indicative; actual weights vary within "
        "mill tolerance. Kg/pc is for a 6 m length. Pipes: tolerance in thickness and weight ±10%. "
        "Availability and prices are confirmed on enquiry.",
        ParagraphStyle("n", fontName=FI, fontSize=8.4, leading=11, textColor=MUTED)))

    for i, s in enumerate(ctx["sections"], start=1):
        compact = len(s["columns"]) <= TWO_COLUMN_MAX_COLS
        if compact:
            story += [NextPageTemplate("two_first"), PageBreak(),
                      SectionHeader(s, i, brand, CONTENT_W), FrameBreak(),
                      _table(s, brand, (CONTENT_W - GUTTER) / 2, True)]
        else:
            story += [NextPageTemplate("one"), PageBreak(),
                      SectionHeader(s, i, brand, CONTENT_W), Spacer(1, 8),
                      _table(s, brand, CONTENT_W, False)]
    return story


def render(ctx):
    """Return (pdf_bytes, page_count, section_pages)."""
    register_fonts()
    brand = _brand(ctx["company"])
    buf = io.BytesIO()
    d1 = CatalogueDoc(buf, ctx, brand, None)
    d1.build(_story(ctx, brand, {}))
    pages, sp = d1.page, d1.section_pages
    buf = io.BytesIO()
    d2 = CatalogueDoc(buf, ctx, brand, pages)
    d2.build(_story(ctx, brand, sp))
    if d2.page != pages or d2.section_pages != sp:
        raise RuntimeError("Page layout changed between passes; contents page numbers would be wrong.")
    return buf.getvalue(), pages, sp


def safe_name(name):
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def generate(store, company_key, out_root):
    """Render, save a dated copy + latest copy, log it. Returns dict with paths."""
    ctx = catalogue.build(store, company_key)
    pdf, pages, _ = render(ctx)
    co = ctx["company"]
    folder = os.path.join(out_root, co["slug"])
    os.makedirs(folder, exist_ok=True)
    stamp = ctx["generated_at"].strftime("%Y-%m-%d_%H%M%S")
    fname = f"{safe_name(co['name'])}_Stock_Catalogue_{stamp}.pdf"
    path = os.path.join(folder, fname)
    with open(path, "wb") as fh:
        fh.write(pdf)
    latest = os.path.join(folder, f"{safe_name(co['name'])}_Stock_Catalogue_LATEST.pdf")
    shutil.copyfile(path, latest)
    store.log_generation(co["id"], "pdf", os.path.relpath(path, out_root), ctx["total"])
    return {"path": path, "latest": latest, "pages": pages, "articles": ctx["total"], "company": co["name"]}
