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

print("ALL TESTS PASSED")
