"""Render every diagram module in this folder to PNG/SVG in ../assets/diagrams. Usage: python make_diagrams.py [name ...]"""
import importlib, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from svgkit import render_all

MODULES = ["diagrams_core", "diagrams_more", "diagrams_data"]
want = set(sys.argv[1:])
jobs = []
for m in MODULES:
    if not (HERE / f"{m}.py").exists():
        continue
    mod = importlib.import_module(m)
    for name, fn in mod.JOBS.items():
        if not want or name in want:
            jobs.append((name, fn()))
render_all(jobs, HERE.parent / "assets" / "diagrams")
print("rendered:", ", ".join(n for n, _ in jobs))
