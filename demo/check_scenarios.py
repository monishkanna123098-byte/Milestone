"""Run both demo scenarios through the real pipeline (Gemini mapping -> whitelist -> Python score).

Usage, from the repo root, with GEMINI_API_KEY in .streamlit/secrets.toml or the environment:
    python demo/check_scenarios.py
Exits 1 if RED doesn't give RED or GREEN doesn't give GREEN.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import core  # noqa: E402
import llm  # noqa: E402

# Read TA from app.py's source: importing app.py would run the Streamlit page.
tree = ast.parse(open("app.py", encoding="utf-8").read())
ta = next(n.value for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "TA")
TA = {k.value: ast.literal_eval(v) for k, v in zip(ta.keys, ta.values)}

data = core.load_data()
age_entry, items = core.checklist_for_age(data, 24)
failed = False
for name, expected in (("demo_red", "RED"), ("demo_green", "GREEN")):
    raw = llm.map_description(TA[name], items, age_entry["label"], data["repetitive_behaviors"])
    if not raw:
        print(f"{name}: Gemini call failed (check GEMINI_API_KEY / network)")
        failed = True
        continue
    mapped = core.validate_mapping(raw, items)
    result = core.score(items, {k: v["status"] for k, v in mapped.items()})
    print(f"\n{name}: {result['level']} (expected {expected}); {len(mapped)}/{len(items)} items mapped")
    for i in items:
        m = mapped.get(i["id"])
        key = "KEY " if core.is_key(i) else "    "
        print(f"  {key}{i['id']:<14} {m['status'] if m else '-':<13} {i['text'][:60]}")
    if result["missing_key"]:
        print("  missing key:", [i["id"] for i in result["missing_key"]])
    failed |= result["level"] != expected
sys.exit(1 if failed else 0)
