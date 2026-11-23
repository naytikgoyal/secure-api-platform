"""Reads the rendered PDF and maps every contents entry (headings, figures, tables) to its displayed page number.
Front matter uses lower-case roman numerals; numbering restarts at 1 on the first page of Chapter 1."""
import json, re, sys
from pathlib import Path
import pymupdf

HERE = Path(__file__).parent
pdf = sys.argv[1]
toc = json.load(open(HERE / "toc.json"))
doc = pymupdf.open(pdf)
norm = lambda s: re.sub(r"\s+", " ", s).strip()
texts = [re.sub(r"^(?:[ivxl]+|\d+)\s+", "", norm(p.get_text())) for p in doc]  # footer number comes first in the text order


def roman(n):
    out = ""
    for v, r in ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out += r; n -= v
    return out


F = next((i for i, t in enumerate(texts) if t.startswith("CHAPTER 1 ")), None)
if F is None:
    print("no Chapter 1 page found"); sys.exit(1)
disp = lambda i: roman(i + 1) if i < F else str(i - F + 1)
pm, miss = {}, []

BODY = ("H:CHAPTER", "H:APPENDIX", "H:REFERENCES", "H:ACHIEVEMENTS")


def find(match, lo, hi, start=True):
    key = norm(match)[:70]
    for i in range(lo, hi):
        t = texts[i]
        if (t.startswith(key) if start else key in t):
            return i
    return None


cur_front, cur_body = 0, F
for e in toc["headings"]:
    isbody = e["id"].startswith(BODY)
    if e["kind"] == "h1":
        i = find(e["match"], cur_body if isbody else cur_front, len(texts) if isbody else F)
        if i is not None:
            pm[e["id"]] = disp(i)
            if isbody: cur_body = i
            else: cur_front = i
        else:
            miss.append(e["id"])
    else:  # h2: search from the current body position, anywhere on the page
        i = find(e["match"], cur_body, len(texts), start=False)
        if i is not None:
            pm[e["id"]] = disp(i); cur_body = i
        else:
            miss.append(e["id"])

# figures and tables: start at the graphical abstract page (front matter) so list pages are never matched
g = find("GRAPHICAL ABSTRACT", 0, F) or F
for kind in ("figures", "tables"):
    cur = g
    for e in toc[kind]:
        i = find(e["match"], cur, len(texts), start=False)
        if i is not None:
            pm[e["id"]] = disp(i); cur = i
        else:
            miss.append(e["id"])

json.dump(pm, open(HERE / "pagemap.json", "w"), indent=1, ensure_ascii=False)
print(f"pages: {len(doc)} (front matter {F}, body {len(doc) - F}); mapped {len(pm)}; missing {len(miss)}")
for m in miss:
    print("  MISSING:", m)
