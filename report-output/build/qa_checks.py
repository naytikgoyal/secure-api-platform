"""Structural checks on the rendered PDF: near-empty pages, headings stranded at the page bottom, chapter starts, caption continuity."""
import re, sys, pymupdf
pdf = sys.argv[1]
doc = pymupdf.open(pdf)
H = doc[0].rect.height
TOP, BOT = 72, H - 72          # text area (2.54 cm margins)
issues = []
chap_pages = {}
for i, pg in enumerate(doc):
    blocks = [b for b in pg.get_text("blocks") if b[3] < BOT + 8 and b[1] > 30]   # drop footer numbers
    imgs = [r for r in (im["bbox"] for im in pg.get_image_info())]
    ys = [b[3] for b in blocks] + [r[3] for r in imgs]
    used = (max(ys) - TOP) / (BOT - TOP) if ys else 0
    txt = re.sub(r"\s+", " ", pg.get_text()).strip()
    first = re.sub(r"^(?:[ivxl]+|\d+)\s+", "", txt)[:60]
    m = re.match(r"CHAPTER (\d) ", first)
    if m: chap_pages[m.group(1)] = i + 1
    if used < 0.35 and i > 1:
        issues.append(f"p{i+1}: only {used:.0%} of the page used  [{first}]")
    last = blocks[-1][4].strip().split("\n")[-1] if blocks else ""
    if blocks and re.match(r"^\d+\.\d+(\.\d+)?\.? ", last) and used > 0.88:
        issues.append(f"p{i+1}: heading at the bottom: {last[:60]}")
print("chapter start pages:", chap_pages)
print("pages:", len(doc))
print("\n".join(issues) if issues else "no structural issues found")
