"""One-off: add spoken-Tamil "ta" text to every milestone and universal check in milestones.json.

Run once, never at app runtime:
    python translate.py            # fills only entries that have no "ta" yet
    python translate.py --force    # re-translates everything

Needs GEMINI_API_KEY in .streamlit/secrets.toml or the environment. One Gemini call per age group,
plus one for the universal checks. English "text" is never changed. Review the output (git diff)
and have a native speaker proofread it before committing.
"""
import json
import os
import sys

from google.genai import types

import core
import llm

PROMPT = """Translate each developmental milestone below into simple spoken Tamil, the way a Chennai
parent talks (Tamil script; common English words like "ball", "toy", "spoon" are fine).

RULES
- Keep the meaning exactly. Do not add or remove anything.
- Phrase it as a question to the parent about their child, like the English.
- Never name any condition or diagnosis.
- Return JSON: {{"<id>": "<Tamil text>", ...}} with exactly the ids given.

MILESTONES
{lines}"""


def translate(entries, force=False):
    todo = [e for e in entries if force or not e.get("ta")]
    if not todo:
        return 0
    lines = "\n".join(f"{e['id']}: {e['text']}" for e in todo)
    resp = llm._client().models.generate_content(
        model=llm.MODEL,
        contents=PROMPT.format(lines=lines),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return core.apply_translations(todo, json.loads(resp.text))


def main():
    force = "--force" in sys.argv
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "milestones.json")
    data = core.load_data(path)
    groups = [(a["label"], a["milestones"]) for a in data["ages"]]
    groups.append(("universal checks", data["universal_checks"]))
    failed = False
    for label, entries in groups:
        try:
            n = translate(entries, force)
            missing = [e["id"] for e in entries if not e.get("ta")]
            print(f"{label}: {n} translated" + (f"; still missing: {missing}" if missing else ""))
            failed |= bool(missing)
        except Exception as e:  # keep going: one bad group shouldn't lose the others
            print(f"{label}: FAILED ({e})")
            failed = True
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    print(f"Wrote {path}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
