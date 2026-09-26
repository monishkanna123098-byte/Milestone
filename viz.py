"""Pure SVG/HTML builders for Mulai. No Streamlit. All text is html-escaped."""
import html
import math
import re

COLOURS = {"observed": "#2e7d32", "unclear": "#f9a825", "not_observed": "#c62828"}
TINTS = {"observed": "#c8e6c9", "unclear": "#ffecb3", "not_observed": "#ffcdd2"}
GREY = "#cfd8dc"
VIDEO_BLUE = "#1565c0"

# (key, Tamil, English, side: -1 left / +1 right, y where the branch leaves the stem)
BRANCHES = [
    ("social", "சமூகம்", "Social", -1, 132),
    ("language", "மொழி", "Language", 1, 198),
    ("thinking", "சிந்தனை", "Thinking", -1, 264),
    ("movement", "இயக்கம்", "Movement", 1, 330),
]
SOIL_Y = 392
BRANCH_LEN = 160

CSS = """
.mulai-sprout{background:#f6faf3;border-radius:14px;padding:6px 0 2px;margin:0 auto}
.mulai-sprout .leaf{transform-box:fill-box;transform-origin:center;
  animation:mulai-grow .5s cubic-bezier(.2,.9,.3,1.25) both}
.mulai-sprout .stem{stroke-dasharray:420;stroke-dashoffset:420;animation:mulai-draw .6s ease-out forwards}
.mulai-sprout .twig{stroke-dasharray:220;stroke-dashoffset:220;animation:mulai-draw .5s ease-out .2s forwards}
@keyframes mulai-grow{from{transform:scale(0)}to{transform:scale(1)}}
@keyframes mulai-draw{to{stroke-dashoffset:0}}
@media (prefers-reduced-motion:reduce){.mulai-sprout .leaf,.mulai-sprout .stem,.mulai-sprout .twig{animation:none;stroke-dashoffset:0}}
"""


def branch_of(item):
    d = (item.get("domain") or "").lower()
    if d.startswith("language"):
        return "language"
    if d.startswith("cognitive"):
        return "thinking"
    if d.startswith(("movement", "physical")):
        return "movement"
    return "social"  # social_emotional, and universal checks (name, eye contact, regression)


def _stem_x(y):
    """Gentle S-curve so the stem isn't a ruler line; deterministic."""
    t = (SOIL_Y - y) / (SOIL_Y - 48)
    return 260 + 9 * math.sin(t * math.pi * 1.6)


def _quad(p0, p1, p2, t):
    return tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c for a, b, c in zip(p0, p1, p2))


def _leaf_path(length):
    w = length * 0.34
    return (f"M0,0 C{length * .25:.1f},{-w:.1f} {length * .75:.1f},{-w:.1f} {length:.1f},0 "
            f"C{length * .75:.1f},{w:.1f} {length * .25:.1f},{w:.1f} 0,0 Z")


def sprout_svg(items, answers, video_ids=(), width=520):
    """One <path class="leaf"> per item. answers: id -> status; missing = not assessed."""
    groups = {b[0]: [] for b in BRANCHES}
    for item in items:
        groups[branch_of(item)].append(item)

    stem_pts = " ".join(f"{_stem_x(y):.1f},{y}" for y in range(SOIL_Y, 47, -8))
    parts = [
        f'<svg class="mulai-sprout" viewBox="0 0 520 420" width="100%" style="max-width:{int(width)}px;display:block" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Milestone sprout">',
        f"<style>{CSS}</style>",
        f'<path d="M20,{SOIL_Y} Q260,{SOIL_Y - 6} 500,{SOIL_Y}" stroke="#8d6e63" stroke-width="3" fill="none"/>',
        f'<ellipse cx="260" cy="{SOIL_Y + 8}" rx="200" ry="14" fill="#d7ccc8" opacity=".6"/>',
        f'<polyline class="stem" points="{stem_pts}" fill="none" stroke="#558b2f" stroke-width="6" '
        f'stroke-linecap="round" stroke-linejoin="round"/>',
        # sprout tip: two small seed-leaves (decorative, not items)
        f'<path d="{_leaf_path(22)}" transform="translate({_stem_x(48):.1f},48) rotate(-150)" fill="#7cb342"/>',
        f'<path d="{_leaf_path(22)}" transform="translate({_stem_x(48):.1f},48) rotate(-30)" fill="#7cb342"/>',
    ]

    n_leaf = 0
    for key, ta, en, side, ay in BRANCHES:
        ax = _stem_x(ay)
        p0, p1, p2 = (ax, ay), (ax + side * 85, ay + 8), (ax + side * BRANCH_LEN, ay - 38)
        parts.append(f'<path class="twig" d="M{p0[0]:.1f},{p0[1]} Q{p1[0]:.1f},{p1[1]} {p2[0]:.1f},{p2[1]}" '
                     f'fill="none" stroke="#689f38" stroke-width="3.5" stroke-linecap="round"/>')
        lx, anchor = p2[0] + side * 8, "start" if side > 0 else "end"
        parts.append(f'<text x="{lx:.1f}" y="{p2[1] - 2:.1f}" text-anchor="{anchor}" font-size="14" '
                     f'font-weight="600" fill="#33691e">{html.escape(ta)}</text>')
        parts.append(f'<text x="{lx:.1f}" y="{p2[1] + 13:.1f}" text-anchor="{anchor}" font-size="11" '
                     f'fill="#6d7b64">{html.escape(en)}</text>')
        leaves = groups[key]
        for k, item in enumerate(leaves):
            t = 0.1 + 0.74 * (k + 1) / (len(leaves) + 1)
            x, y = _quad(p0, p1, p2, t)
            dx, dy = (2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0]),
                      2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1]))
            angle = math.degrees(math.atan2(dy, dx)) + (-48 if k % 2 == 0 else 48) * side
            status = answers.get(item["id"])
            if status == "not_observed":
                angle += 32 if math.cos(math.radians(angle)) >= 0 else -32  # droop
            big = item.get("autism_sign") or "applies_from_months" in item  # universal checks
            length = 40 if big else 29
            if status in COLOURS:
                fill, stroke, sw = COLOURS[status], "none", 0
            else:
                fill, stroke, sw = "#ffffff", GREY, 2
            if item["id"] in video_ids:
                stroke, sw = VIDEO_BLUE, 2.5
            parts.append(
                f'<g transform="translate({x:.1f},{y:.1f}) rotate({angle:.1f})">'
                f'<path class="leaf" d="{_leaf_path(length)}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw}" style="animation-delay:{300 + 40 * n_leaf}ms">'
                f"<title>{html.escape(item['text'])}</title></path></g>")
            n_leaf += 1
    parts.append("</svg>")
    return "".join(parts)


def legend_html(show_video=False):
    entries = [(COLOURS["observed"], "none", "ஆம் · Yes"), (COLOURS["unclear"], "none", "தெரியல · Not sure"),
               (COLOURS["not_observed"], "none", "இல்லை · Not yet"), ("#ffffff", GREY, "Not asked"),
               ("#7cb342", "none", "Bigger leaf = key sign")]
    if show_video:
        entries.append(("#ffffff", VIDEO_BLUE, "Seen in video"))
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin:4px 12px 4px 0">'
        f'<svg width="26" height="14" viewBox="-1 -8 30 16"><path d="{_leaf_path(28)}" fill="{f}" '
        f'stroke="{s}" stroke-width="2"/></svg>{html.escape(label)}</span>'
        for f, s, label in entries)
    return f'<div style="font-size:13px;color:#546e7a;text-align:center;margin-top:6px">{chips}</div>'


def highlight_html(parent_text, mapped, items=()):
    """Parent's text, escaped first, with each verbatim quote wrapped in a <mark> in its status colour."""
    names = {i["id"]: i["text"] for i in items}
    safe = html.escape(parent_text or "")
    spans = []
    for item_id, m in mapped.items():
        quote = (m.get("quote") or "").strip()
        if not quote or m.get("status") not in TINTS:
            continue
        hit = re.search(re.escape(html.escape(quote)), safe, re.IGNORECASE)
        if hit and not any(hit.start() < e and s < hit.end() for s, e, _, _ in spans):
            spans.append((hit.start(), hit.end(), m["status"], names.get(item_id, item_id)))
    out, pos = [], 0
    for s, e, status, name in sorted(spans):
        out.append(safe[pos:s])
        out.append(f'<mark title="{html.escape(name, quote=True)}" style="background:{TINTS[status]};'
                   f'border-bottom:2px solid {COLOURS[status]};padding:0 2px;border-radius:3px;color:inherit">'
                   f"{safe[s:e]}</mark>")
        pos = e
    out.append(safe[pos:])
    return ('<div style="white-space:pre-wrap;line-height:1.7;font-size:1.05rem;padding:12px 14px;'
            f'border-left:4px solid #7cb342;background:rgba(124,179,66,.08);border-radius:6px">{"".join(out)}</div>')
