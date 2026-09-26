import core
import viz

data = core.load_data()

# Age selection
entry, items = core.checklist_for_age(data, 20)
assert entry["age_months"] == 18, entry["age_months"]
try:
    core.checklist_for_age(data, 11)
    assert False, "expected ValueError"
except ValueError:
    pass

ids = {i["id"] for i in items}
assert {"m18_se2", "m18_mp2", "u_regression"} <= ids, "expected ids missing from 18-month checklist"

# validate_mapping is the security boundary
raw = {"items": [
    {"id": "m18_se2", "status": "observed", "quote": "yes he does"},
    {"id": "hacked_id", "status": "observed", "quote": "x"},
    {"id": "m18_mp2", "status": "green", "quote": "y"},
]}
mapped = core.validate_mapping(raw, items)
assert "hacked_id" not in mapped
assert "m18_mp2" not in mapped
assert mapped["m18_se2"] == {"status": "observed", "quote": "yes he does"}

# Scoring
all_obs = {i: "observed" for i in ids}
assert core.score(items, all_obs)["level"] == "GREEN"
assert core.score(items, {**all_obs, "m18_se2": "not_observed"})["level"] == "RED"
assert core.score(items, {**all_obs, "m18_mp2": "not_observed"})["level"] == "AMBER"
assert core.score(items, {**all_obs, "u_regression": "not_observed"})["level"] == "RED"

# GREEN coverage guard
key_ids = [i["id"] for i in items if core.is_key(i)]
assert "u_regression" in key_ids and "m18_se2" in key_ids
one = core.score(items, {"m18_mp2": "observed"})  # 1 observed, rest skipped
assert one["level"] == "INCOMPLETE", one["level"]
assert {i["id"] for i in one["missing_key"]} == set(key_ids)
assert len(one["not_assessed"]) == len(items) - 1

need = -(-3 * len(items) // 5)  # ceil(60%)
enough = {k: "observed" for k in key_ids}
for i in items:
    if len(enough) >= need:
        break
    enough.setdefault(i["id"], "observed")
assert core.score(items, enough)["level"] == "GREEN"
enough_unclear_key = {**enough, key_ids[0]: "unclear"}  # "unclear" counts as answered (and makes it AMBER)
assert core.score(items, enough_unclear_key)["level"] == "AMBER"

only_key = {k: "observed" for k in key_ids}
if len(only_key) < need:  # all key answered but under 60% -> still INCOMPLETE, no missing key
    r = core.score(items, only_key)
    assert r["level"] == "INCOMPLETE" and r["missing_key"] == [] and r["more_needed"] == need - len(only_key)

assert core.score(items, {"m18_se2": "not_observed"})["level"] == "RED"  # key not_observed, rest skipped
assert core.score(items, {"m18_mp2": "not_observed"})["level"] == "AMBER"  # AMBER fires with partial answers

# Every activity id in app.py must exist in milestones.json (read from source: importing app.py runs the page)
import ast
import os
tree = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"), encoding="utf-8").read())
activity_ids = next([k.value for k in node.value.keys] for node in tree.body
                    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ACTIVITIES")
missing_activity = sorted(set(activity_ids) - core.all_ids(data))
assert not missing_activity, f"ACTIVITIES ids not in milestones.json: {missing_activity}"

# Consent texts: README must quote them word for word; every level has a safe Tamil voice template
consts = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
          and getattr(n.targets[0], "id", "") in ("CONSENT_TEXT", "VIDEO_CONSENT_TEXT", "TA")}
readme = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"), encoding="utf-8").read()
for name in ("CONSENT_TEXT", "VIDEO_CONSENT_TEXT"):
    assert consts[name] in readme, f"README must quote {name} word for word"
for level in ("red", "amber", "green", "incomplete"):
    tpl = consts["TA"][f"voice_{level}"]
    assert tpl and not core.BANNED_RE.search(tpl), level
assert core.BANNED_RE.search("இது ஆட்டிசம் மாதிரி") and core.BANNED_RE.search("Autistic traits")

# Video: validate_video is the security boundary for model output
raw_video = {"observations": [
    {"id": "m18_se2", "finding": "observed", "timestamp": "00:06", "description": "points at the fan"},
    {"id": "hacked_id", "finding": "observed", "timestamp": "00:07", "description": "x"},
    {"id": "m18_mp2", "finding": "cannot_walk", "timestamp": "00:08", "description": "x"},
    {"id": "m18_mp2", "finding": "observed", "timestamp": "4 seconds", "description": "x"},
    {"id": "u_regression", "finding": "observed", "timestamp": "00:09", "description": "x"},
]}
obs = core.validate_video(raw_video, items)
assert [(o["id"], o["timestamp"]) for o in obs] == [("m18_se2", "00:06")], obs
assert core.validate_video("garbage", items) == []
assert "autis" not in core.sanitize("looks autistic, autism signs").lower()
assert "[removed]" in core.sanitize("ஆட்டிசம் இருக்கலாம்")

# compare: the four verdicts
some = [i["id"] for i in items if not i.get("is_regression_check")][:4]
video_obs = [
    {"id": some[0], "text": "a", "finding": "observed", "timestamp": "00:01", "description": ""},
    {"id": some[1], "text": "b", "finding": "observed", "timestamp": "00:02", "description": ""},
    {"id": some[2], "text": "c", "finding": "opportunity_not_observed", "timestamp": "00:03", "description": ""},
    {"id": some[3], "text": "d", "finding": "opportunity_not_observed", "timestamp": "00:04", "description": ""},
]
parent = {some[0]: "observed", some[1]: "not_observed", some[2]: "observed", some[3]: "unclear"}
before = dict(parent)
verdicts = {r["id"]: r["verdict"] for r in core.compare(parent, video_obs)}
assert verdicts == {some[0]: "confirmed", some[1]: "video_shows_skill",
                    some[2]: "worth_watching", some[3]: "consistent_concern"}, verdicts
assert parent == before, "compare must not modify parent_answers"
assert core.compare({}, video_obs[:1])[0]["verdict"] == "video_shows_skill"  # not assessed + seen

# Tamil translations: only known ids, clean strings, no condition names; English text untouched
entries = [{"id": "a", "text": "Waves bye-bye"}, {"id": "b", "text": "Points"}, {"id": "c", "text": "Walks"}]
n = core.apply_translations(entries, {"a": " டாட்டா காட்டுதா? ", "b": "ஆட்டிசம் அடையாளம்", "c": 5, "zz": "x"})
assert n == 1 and entries[0]["ta"] == "டாட்டா காட்டுதா?" and entries[0]["text"] == "Waves bye-bye"
assert "ta" not in entries[1] and "ta" not in entries[2]
assert core.apply_translations(entries, ["not", "a", "dict"]) == 0

# Repetitive behaviours: reported in the note, never scored
all_obs_result = core.score(items, all_obs)
note = core.doctor_note(20, entry, items, all_obs, {}, all_obs_result, ["Lines up toys"])
assert "Lines up toys" in note and "not scored" in note and all_obs_result["level"] == "GREEN"

# Visuals
answers_mix = {items[0]["id"]: "observed", items[1]["id"]: "not_observed", items[2]["id"]: "unclear"}
svg = viz.sprout_svg(items, answers_mix)
assert svg.count('class="leaf"') == len(items), (svg.count('class="leaf"'), len(items))
assert svg == viz.sprout_svg(items, answers_mix), "sprout must be deterministic"
still = viz.sprout_svg(items, answers_mix, animate=False)
assert still.count('class="leaf"') == len(items) and "animation" not in still and "@keyframes" not in still
assert "animation-delay" in svg
assert viz.sprout_svg(items, answers_mix, {items[0]["id"]}).count("#1565c0") == 1  # one video ring

evil = "<script>alert(1)</script> he says amma"
hl = viz.highlight_html(evil, {"m18_se2": {"status": "observed", "quote": "SAYS AMMA"}}, items)
assert "<script" not in hl and "&lt;script&gt;" in hl
assert hl.count("<mark") == 1 and ">says amma</mark>" in hl  # case-insensitive, keeps parent's casing
assert viz.highlight_html(evil, {"m18_se2": {"status": "observed", "quote": "not in text"}}).count("<mark") == 0
assert "<script" not in viz.sprout_svg([{**items[0], "text": "<script>x</script>"}], {})
assert hl == viz.highlight_html(evil, {"m18_se2": {"status": "observed", "quote": "SAYS AMMA"}}, items)

print("ALL TESTS PASSED")
