"""Pure logic for Mulai. No Streamlit, no network."""
import json
from datetime import date

STATUSES = ("observed", "not_observed", "unclear")


def load_data(path="milestones.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def checklist_for_age(data, age_months):
    if age_months < 12 or age_months > 71:
        raise ValueError("Age must be between 12 and 71 months.")
    eligible = [a for a in data["ages"] if a["age_months"] <= age_months]
    age_entry = max(eligible, key=lambda a: a["age_months"])
    universal = [u for u in data["universal_checks"] if u["applies_from_months"] <= age_months]
    return age_entry, list(age_entry["milestones"]) + universal


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
    level = "RED" if red else "AMBER" if amber else "GREEN"
    return {"level": level, "missed": missed, "unclear": unclear,
            "not_assessed": not_assessed, "reasons": reasons}


def doctor_note(age_months, age_entry, items, answers, quotes, result, repetitive):
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
    lines += [
        "",
        "---",
        "Screening aid based on CDC 'Learn the Signs. Act Early.' milestones. "
        "Not a diagnosis. Please discuss with your child's doctor.",
    ]
    return "\n".join(lines) + "\n"
