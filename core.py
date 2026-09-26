"""Pure logic for MilestoneAI. No Streamlit, no network."""
import json
import os
import re
from datetime import date

STATUSES = ("observed", "not_observed", "unclear")
GREEN_MIN_COVERAGE = (3, 5)  # 60%, as a fraction so the threshold is exact
VIDEO_FINDINGS = ("observed", "opportunity_not_observed")
TIMESTAMP_RE = re.compile(r"^\d{1,2}:\d{2}$")
BANNED_RE = re.compile(r"autis\w*|\bASD\b|ஆட்டி[சஸ]\S*|மதி\s*இறுக்க\S*", re.IGNORECASE)


def load_data(path="milestones.json"):
    """Read the checklist. A relative path that isn't found from the current directory is looked up
    next to this file, so the app works whichever folder the host starts it from."""
    if not os.path.isabs(path) and not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def checklist_for_age(data, age_months):
    if age_months < 12 or age_months > 71:
        raise ValueError("Age must be between 12 and 71 months.")
    eligible = [a for a in data["ages"] if a["age_months"] <= age_months]
    age_entry = max(eligible, key=lambda a: a["age_months"])
    universal = [u for u in data["universal_checks"] if u["applies_from_months"] <= age_months]
    return age_entry, list(age_entry["milestones"]) + universal


def all_ids(data):
    """Every milestone id across all ages, plus universal checks."""
    return {m["id"] for a in data["ages"] for m in a["milestones"]} | {u["id"] for u in data["universal_checks"]}


def is_key(item):
    """Key items: autism_sign items and every applicable universal check (incl. regression)."""
    return bool(item.get("autism_sign")) or "applies_from_months" in item


def validate_mapping(raw, items):
    """Security boundary: only whitelisted ids and exact statuses survive."""
    valid_ids = {i["id"] for i in items}
    out = {}
    entries = raw.get("items", []) if isinstance(raw, dict) else []
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict):
            continue
        item_id, status = e.get("id"), e.get("status")
        if item_id in valid_ids and status in STATUSES:
            quote = e.get("quote")
            out[item_id] = {"status": status, "quote": quote if isinstance(quote, str) else ""}
    return out


def apply_translations(entries, raw):
    """Set a "ta" field on milestone entries from model output {id: Tamil text}. Only known ids,
    non-empty strings and text without condition names are kept; "text" is never touched.
    Returns the number of entries updated."""
    by_id = {e["id"]: e for e in entries}
    count = 0
    for item_id, ta in (raw.items() if isinstance(raw, dict) else []):
        if item_id in by_id and isinstance(ta, str) and ta.strip() and not BANNED_RE.search(ta):
            by_id[item_id]["ta"] = ta.strip()
            count += 1
    return count


def sanitize(text):
    """Remove condition names from model text."""
    return BANNED_RE.sub("[removed]", text) if isinstance(text, str) else ""


def ts_seconds(ts):
    m, s = ts.split(":")
    return int(m) * 60 + int(s)


def validate_video(raw, items):
    """Security boundary for video output: whitelisted ids, exact findings, mm:ss timestamps.
    Regression items are excluded: one clip cannot show lost skills."""
    by_id = {i["id"]: i for i in items if not i.get("is_regression_check")}
    obs = raw.get("observations", []) if isinstance(raw, dict) else []
    out = []
    for o in obs if isinstance(obs, list) else []:
        if not isinstance(o, dict):
            continue
        item, ts = by_id.get(o.get("id")), o.get("timestamp")
        if (item and o.get("finding") in VIDEO_FINDINGS and isinstance(ts, str)
                and TIMESTAMP_RE.match(ts) and int(ts.split(":")[1]) < 60):
            out.append({"id": item["id"], "text": item["text"], "finding": o["finding"],
                        "timestamp": ts, "description": sanitize(o.get("description"))})
    return out


def compare(parent_answers, video_obs):
    """One row per item with video evidence. Never modifies parent_answers.
    If the clip shows a skill at least once, that observation wins."""
    best = {}
    for o in video_obs:
        if o["id"] not in best or (o["finding"] == "observed" and best[o["id"]]["finding"] != "observed"):
            best[o["id"]] = o
    rows = []
    for item_id, o in best.items():
        parent = parent_answers.get(item_id) or "not_assessed"
        if o["finding"] == "observed":
            verdict = "confirmed" if parent == "observed" else "video_shows_skill"
        elif parent in ("not_observed", "unclear"):
            verdict = "consistent_concern"
        else:
            # parent said observed, or did not answer: one missed chance in one clip is not enough
            verdict = "worth_watching"
        rows.append({"id": item_id, "text": o["text"], "parent": parent, "video": o["finding"],
                     "timestamp": o["timestamp"], "description": o["description"], "verdict": verdict})
    return rows


def score(items, answers):
    missed, unclear, not_assessed, reasons = [], [], [], []
    red = amber = False
    for item in items:
        status = answers.get(item["id"])
        if status not in STATUSES:
            not_assessed.append(item)
            continue
        if status == "not_observed":
            missed.append(item)
            if item.get("is_regression_check"):
                red = True
                reasons.append("Your child has lost skills they used to have.")
            elif item.get("autism_sign"):
                red = True
                reasons.append(f"Not yet seen: {item['text']}")
            else:
                amber = True
                reasons.append(f"Not yet seen: {item['text']}")
        elif status == "unclear":
            unclear.append(item)
            amber = True
            reasons.append(f"Not sure: {item['text']}")
    # GREEN needs every key item answered ("unclear" counts) and >= 60% of all items answered.
    missing_key = [i for i in not_assessed if is_key(i)]
    answered = len(items) - len(not_assessed)
    num, den = GREEN_MIN_COVERAGE
    more_needed = max(0, -(-num * len(items) // den) - answered)  # ceil(60% of items) - answered
    if red:
        level = "RED"
    elif amber:
        level = "AMBER"
    elif not missing_key and not more_needed:
        level = "GREEN"
    else:
        level = "INCOMPLETE"
    return {"level": level, "missed": missed, "unclear": unclear, "not_assessed": not_assessed,
            "reasons": reasons, "missing_key": missing_key, "more_needed": more_needed}


def doctor_note(age_months, age_entry, items, answers, quotes, result, repetitive,
                video_rows=None, video_repetitive=None):
    lost = any(i.get("is_regression_check") and answers.get(i["id"]) == "not_observed" for i in items)
    lines = [
        "# Developmental milestones check – note for the doctor",
        "",
        f"- **Date:** {date.today().isoformat()}",
        f"- **Child's age:** {age_months} months",
        f"- **Checklist used:** CDC {age_entry['label']} ({age_entry['url']})",
        f"- **Result:** {result['level']}",
        f"- **Lost skills reported:** {'Yes' if lost else 'No'}",
        "",
        "## Milestones not yet seen",
    ]
    missed = [i for i in result["missed"] if not i.get("is_regression_check")]
    for i in missed:
        q = quotes.get(i["id"])
        lines.append(f"- {i['text']}" + (f' — parent said: "{q}"' if q else ""))
    if not missed:
        lines.append("- None")
    lines += ["", "## Parent was not sure"]
    lines += [f"- {i['text']}" for i in result["unclear"]] or ["- None"]
    lines += ["", "## Not assessed"]
    lines += [f"- {i['text']}" for i in result["not_assessed"]] or ["- None"]
    lines += ["", "## Repetitive behaviours reported by parent (not scored)"]
    lines += [f"- {r}" for r in repetitive] or ["- None reported"]
    if video_rows or video_repetitive:
        lines += ["", "## Home video observations"]
        for r in sorted(video_rows, key=lambda r: ts_seconds(r["timestamp"])):
            seen = f" — {r['description']}" if r["description"] else ""
            lines.append(f"- {r['timestamp']} · {r['text']}{seen} · {r['verdict'].replace('_', ' ')}")
        for ts, behaviour in video_repetitive or []:
            lines.append(f"- {ts} · Repetitive behaviour seen: {behaviour} · not scored")
        lines.append("")
        lines.append("_Observations generated by AI from a parent-provided clip; please review the original video._")
    lines += [
        "",
        "---",
        "Screening aid based on CDC 'Learn the Signs. Act Early.' milestones. "
        "Not a diagnosis. Please discuss with your child's doctor.",
    ]
    return "\n".join(lines) + "\n"
