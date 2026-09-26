import core

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

partial = core.score(items, {"m18_mp2": "observed"})
assert partial["level"] == "GREEN"
assert len(partial["not_assessed"]) == len(items) - 1

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

print("ALL TESTS PASSED")
