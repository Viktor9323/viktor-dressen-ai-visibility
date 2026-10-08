#!/usr/bin/env python3
"""Сборка фирменного PDF-отчёта AI Visibility Audit (Виктор Дрессен · Яклик).

Использование:
    python3 make_pdf.py report.md -o audit.pdf

Вход — Markdown по шаблону templates/report.md. Поддерживается:
# заголовок отчёта, ## / ### разделы, абзацы, списки (- и 1.),
таблицы |...|, **жирный**, *курсив*, [текст](ссылка), > цитата, ---.

На каждой странице — колонтитул с кликабельными ссылками на Telegram
Виктора Дрессена и сайт агентства Яклик. В конце — контактный блок.
"""
import argparse
import os
import re
import sys
from datetime import date

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)
    from reportlab.platypus.flowables import HRFlowable
except ImportError:
    sys.exit("Нужна библиотека reportlab: pip install reportlab "
             "(в некоторых окружениях: pip install reportlab --break-system-packages)")

# ---------- Бренд ----------
AUTHOR = "Виктор Дрессен"
ROLE = "руководитель агентства Яклик"
TG_URL = "https://t.me/Viktor_Dressen"
TG_LABEL = "t.me/Viktor_Dressen"
SITE_URL = "https://yaklik.ru"
SITE_LABEL = "yaklik.ru"

SAGE = colors.HexColor("#6F8F72")       # основной шалфейный
SAGE_DARK = colors.HexColor("#3F5A43")
SAGE_LIGHT = colors.HexColor("#E8EFE6")
INK = colors.HexColor("#1F2A22")
MUTED = colors.HexColor("#6B7568")
LINE = colors.HexColor("#CBD6C8")

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")


def register_fonts():
    pdfmetrics.registerFont(TTFont("DV", os.path.join(FONTS, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DV-B", os.path.join(FONTS, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DV-I", os.path.join(FONTS, "DejaVuSans-Oblique.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")


def styles():
    base = dict(fontName="DV", textColor=INK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("title", fontSize=20, leading=25, fontName="DV-B",
                                textColor=colors.white, **{k: v for k, v in base.items()
                                                           if k not in ("fontName", "textColor")}),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, leading=14,
                                   textColor=colors.HexColor("#F2F6F1"), fontName="DV"),
        "h2": ParagraphStyle("h2", fontSize=14, leading=18, spaceBefore=12, spaceAfter=6,
                             fontName="DV-B", textColor=SAGE_DARK, keepWithNext=1),
        "h3": ParagraphStyle("h3", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4,
                             fontName="DV-B", textColor=INK, keepWithNext=1),
        "body": ParagraphStyle("body", fontSize=10, leading=14.5, spaceAfter=5, **base),
        "bullet": ParagraphStyle("bullet", fontSize=10, leading=14.5, leftIndent=14,
                                 bulletIndent=3, spaceAfter=2, **base),
        "quote": ParagraphStyle("quote", fontSize=9.5, leading=13.5, leftIndent=10,
                                textColor=MUTED, fontName="DV-I", spaceAfter=6),
        "cell": ParagraphStyle("cell", fontSize=8.8, leading=11.5, **base),
        "cellh": ParagraphStyle("cellh", fontSize=8.8, leading=11.5, fontName="DV-B",
                                textColor=colors.white),
        "contact": ParagraphStyle("contact", fontSize=10.5, leading=16, **base),
    }


# ---------- Inline-разметка ----------
MARKS = {
    "✅": '<font color="#2E7D32">✔ да</font>',
    "⚠️": '<font color="#B26A00">◐ частично</font>',
    "⚠": '<font color="#B26A00">◐ частично</font>',
    "❌": '<font color="#C62828">✘ нет</font>',
}


def inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    placeholders = {}
    for i, (emo, rep) in enumerate(MARKS.items()):
        key = f"\x00{i}\x00"
        if emo in text:
            text = text.replace(emo, key)
            placeholders[key] = rep
    text = text.replace("️", "")
    link_color = SAGE_DARK.hexval().replace("0x", "#")

    def link(m):
        label, url = m.group(1), m.group(2).replace('"', "%22")
        return f'<a href="{url}" color="{link_color}"><u>{label}</u></a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"(?<![\"=/])(https?://[^\s<)]+)",
                  lambda m: f'<a href="{m.group(1)}" color="{link_color}"><u>{m.group(1)}</u></a>',
                  text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="DV" color="#3F5A43">\1</font>', text)
    for key, rep in placeholders.items():
        text = text.replace(key, rep)
    return text


# ---------- Разбор Markdown ----------
def parse(md, st, width):
    title, subtitle = None, None
    flow = []
    lines = md.splitlines()
    i = 0
    para = []

    def flush():
        if para:
            flow.append(Paragraph(inline(" ".join(para)), st["body"]))
            para.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()

        if s.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            txt = "<br/>".join(c.replace("&", "&amp;").replace("<", "&lt;")
                               .replace(">", "&gt;").replace(" ", "&nbsp;") for c in code)
            t = Table([[Paragraph(txt, ParagraphStyle("code", fontName="DV", fontSize=7.5,
                                                      leading=10, textColor=INK))]],
                      colWidths=[width])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SAGE_LIGHT),
                                   ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                   ("TOPPADDING", (0, 0), (-1, -1), 5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            flow += [t, Spacer(1, 6)]
            i += 1
            continue

        if s.startswith("<!--"):
            flush()
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
        elif not s:
            flush()
        elif s.startswith("# ") and title is None:
            flush()
            title = s[2:].strip()
            # первая непустая строка после заголовка — подзаголовок
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not lines[j].strip().startswith(("#", "|", "-", ">")):
                subtitle = lines[j].strip()
                i = j
        elif s.startswith("### "):
            flush()
            flow.append(Paragraph(inline(s[4:]), st["h3"]))
        elif s.startswith("## ") or s.startswith("# "):
            flush()
            flow.append(Paragraph(inline(s.lstrip("#").strip()), st["h2"]))
            hr = HRFlowable(width="100%", thickness=0.8, color=SAGE, spaceAfter=6)
            hr.keepWithNext = 1
            flow.append(hr)
        elif re.fullmatch(r"-{3,}|\*{3,}", s):
            flush()
            flow.append(HRFlowable(width="100%", thickness=0.5, color=LINE,
                                   spaceBefore=6, spaceAfter=6))
        elif s.startswith(">"):
            flush()
            flow.append(Paragraph(inline(s.lstrip("> ").strip()), st["quote"]))
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                r = lines[i].strip().strip("|")
                cells = [c.strip() for c in r.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            flow.append(make_table(rows, st, width))
            flow.append(Spacer(1, 8))
            continue
        elif re.match(r"^[-*•]\s+", s):
            flush()
            flow.append(Paragraph(inline(re.sub(r"^[-*•]\s+", "", s)), st["bullet"],
                                  bulletText="•"))
        elif re.match(r"^\d+[.)]\s+", s):
            flush()
            num = re.match(r"^(\d+)", s).group(1)
            flow.append(Paragraph(inline(re.sub(r"^\d+[.)]\s+", "", s)), st["bullet"],
                                  bulletText=f"{num}."))
        else:
            para.append(s)
        i += 1
    flush()
    return title, subtitle, flow


def _plain(cell):
    cell = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cell)
    cell = cell.replace("**", "").replace("`", "")
    cell = cell.replace("✅", "✔ да").replace("❌", "✘ нет")
    cell = cell.replace("⚠️", "◐ частично").replace("⚠", "◐ частично")
    return cell


def column_widths(rows, ncol, width):
    """Колонка не уже самого длинного слова; остальное — пропорционально тексту."""
    fs, pad = 8.8, 11
    mins, wants = [], []
    for c in range(ncol):
        cells = [_plain(r[c]) for r in rows]
        words = [w for cell in cells for w in cell.split()] or [""]
        longest = max(pdfmetrics.stringWidth(w, "DV-B", fs) for w in words)
        full = max(pdfmetrics.stringWidth(cell, "DV", fs) for cell in cells)
        mins.append(longest + pad)
        wants.append(max(min(full + pad, width * 0.6), longest + pad))
    if sum(wants) <= width:
        extra = width - sum(wants)
        total = sum(wants)
        return [w + extra * w / total for w in wants]
    if sum(mins) >= width:
        return [width * m / sum(mins) for m in mins]
    flex = [w - m for w, m in zip(wants, mins)]
    room = width - sum(mins)
    return [m + room * f / sum(flex) for m, f in zip(mins, flex)]


def make_table(rows, st, width):
    if not rows:
        return Spacer(1, 1)
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    widths = column_widths(rows, ncol, width)
    data = []
    for ri, r in enumerate(rows):
        style = st["cellh"] if ri == 0 else st["cell"]
        data.append([Paragraph(inline(c), style) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SAGE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SAGE_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def contact_block(st, width):
    link_color = SAGE_DARK.hexval().replace("0x", "#")
    txt = (f'<font name="DV-B" size="12" color="{link_color}">Нужна помощь с внедрением?</font><br/>'
           f"Агентство Яклик доработает карточку, прайс, отзывы и сайт так, чтобы нейросети "
           f"могли рекомендовать вашу организацию.<br/><br/>"
           f'<b>{AUTHOR}</b>, {ROLE}<br/>'
           f'Telegram: <a href="{TG_URL}" color="{link_color}"><u>{TG_LABEL}</u></a><br/>'
           f'Сайт агентства: <a href="{SITE_URL}" color="{link_color}"><u>{SITE_LABEL}</u></a>')
    t = Table([[Paragraph(txt, st["contact"])]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAGE_LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 4, SAGE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return KeepTogether([Spacer(1, 14), t])


def build(md_path, out_path):
    register_fonts()
    st = styles()
    with open(md_path, encoding="utf-8") as f:
        md = f.read()

    page_w, page_h = A4
    lm = rm = 16 * mm
    width = page_w - lm - rm
    title, subtitle, flow = parse(md, st, width)
    title = title or "Аудит видимости в нейросетях"
    subtitle = subtitle or f"{date.today():%d.%m.%Y} · {AUTHOR}, агентство Яклик"
    # высота шапки считается по фактической высоте заголовка
    _, title_h = Paragraph(inline(title), st["title"]).wrap(width, page_h)
    _, sub_h = Paragraph(inline(subtitle), st["subtitle"]).wrap(width, page_h)
    header_h = 15 * mm + title_h + 3 * mm + sub_h + 7 * mm

    def footer(c, doc):
        c.saveState()
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(lm, 14 * mm, page_w - rm, 14 * mm)
        c.setFont("DV", 8)
        c.setFillColor(MUTED)
        left = f"{AUTHOR} · агентство Яклик"
        c.drawString(lm, 9.5 * mm, left)
        # кликабельные ссылки справа
        x = page_w - rm
        c.setFillColor(SAGE_DARK)
        for label, url in ((SITE_LABEL, SITE_URL), (TG_LABEL, TG_URL)):
            w = pdfmetrics.stringWidth(label, "DV", 8)
            c.drawString(x - w, 9.5 * mm, label)
            c.linkURL(url, (x - w, 8.5 * mm, x, 12.5 * mm), relative=0)
            x -= w + 12
        c.setFillColor(MUTED)
        c.drawCentredString(page_w / 2, 9.5 * mm, str(doc.page))
        c.restoreState()

    def first_page(c, doc):
        c.saveState()
        c.setFillColor(SAGE_DARK)
        c.rect(0, page_h - header_h, page_w, header_h, stroke=0, fill=1)
        c.setFillColor(SAGE)
        c.rect(0, page_h - header_h, page_w, 2.2 * mm, stroke=0, fill=1)
        # бренд
        c.setFillColor(colors.HexColor("#DDE7DB"))
        c.setFont("DV-B", 8.5)
        c.drawString(lm, page_h - 9 * mm, "ЯКЛИК · AI VISIBILITY AUDIT")
        tw = pdfmetrics.stringWidth(TG_LABEL, "DV", 8.5)
        c.setFont("DV", 8.5)
        c.drawString(page_w - rm - tw, page_h - 9 * mm, TG_LABEL)
        c.linkURL(TG_URL, (page_w - rm - tw, page_h - 10.5 * mm, page_w - rm, page_h - 6.5 * mm),
                  relative=0)
        # заголовок
        p = Paragraph(inline(title), st["title"])
        p.wrap(width, header_h)
        p.drawOn(c, lm, page_h - 15 * mm - title_h)
        s = Paragraph(inline(subtitle), st["subtitle"])
        s.wrap(width, header_h)
        s.drawOn(c, lm, page_h - 15 * mm - title_h - 3 * mm - sub_h)
        c.restoreState()
        footer(c, doc)

    doc = SimpleDocTemplate(
        out_path, pagesize=A4, leftMargin=lm, rightMargin=rm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=title, author=f"{AUTHOR}, агентство Яклик",
        subject="Аудит видимости карточки в нейросетях",
    )
    story = [Spacer(1, header_h - 8 * mm)] + flow + [contact_block(st, width)]
    doc.build(story, onFirstPage=first_page, onLaterPages=footer)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    out = a.output or os.path.splitext(a.markdown)[0] + ".pdf"
    print(build(a.markdown, out))


if __name__ == "__main__":
    main()
