import streamlit as st

import core
import llm

st.set_page_config(page_title="Mulai – early signs check", page_icon="🌱")

REGRESSION_Q = "Has your child stopped doing something they used to do (words, gestures, play)?"
EMOJI = {"observed": "✅", "not_observed": "❌", "unclear": "❓"}
BANNER = {
    "RED": ("#c62828", "Please book a doctor visit now and ask about developmental screening."),
    "AMBER": ("#ef6c00", "Mention these at your child's next doctor visit."),
    "GREEN": ("#2e7d32", "Your child is doing what most children do at this age. "
                         "Keep tracking, and talk to your doctor if you ever worry."),
}


def to_status(item, choice):
    if choice in (None, "Skip"):
        return None
    if item.get("is_regression_check"):
        return {"Yes": "not_observed", "No": "observed", "Not sure": "unclear"}[choice]
    return {"Yes": "observed", "No": "not_observed", "Not sure": "unclear"}[choice]


def to_choice(item, status):
    if item.get("is_regression_check"):
        return {"not_observed": "Yes", "observed": "No", "unclear": "Not sure"}[status]
    return {"observed": "Yes", "not_observed": "No", "unclear": "Not sure"}[status]


def question(item):
    return REGRESSION_Q if item.get("is_regression_check") else item["text"]


st.title("முளை · Mulai")
st.write("குழந்தையின் வளர்ச்சி அடையாளங்களை முன்கூட்டியே கவனிப்போம் · "
         "Notice your child's early developmental signs, early.")

# Step 1: consent
consent = st.checkbox("I am the child's parent/guardian and I agree to this check. "
                      "No name is collected. Nothing is stored after I close this page.")
st.caption("Consent as per DPDP Act 2023, Sec. 9")
if not consent:
    st.stop()

data = core.load_data()
ss = st.session_state
ss.setdefault("run", 0)

# Step 2: age
age = int(st.number_input("Child's age in months", min_value=12, max_value=71, value=18, step=1))
try:
    age_entry, items = core.checklist_for_age(data, age)
except ValueError as e:
    st.error(str(e))
    st.stop()
st.caption(f"We will use the CDC {age_entry['label']} checklist.")

if ss.get("checked_age") not in (None, age):
    for k in ("checked_age", "mapped", "repetitive", "llm_failed", "result"):
        ss.pop(k, None)

# Step 3: describe
text = st.text_area(
    "Tell us about your child · உங்கள் குழந்தையைப் பற்றி சொல்லுங்கள்",
    placeholder="பெயர் சொன்னால் திரும்பிப் பார்க்கிறதா? விரலால் சுட்டிக் காட்டுகிறதா? என்ன வார்த்தைகள் பேசுகிறது? "
                "மற்ற குழந்தைகளுடன் விளையாடுகிறதா? நீங்கள் செய்வதைப் பார்த்துச் செய்கிறதா?\n"
                "Does your child respond to their name? Point at things? Which words do they say? "
                "Play with others? Copy what you do?",
    height=160,
)
if st.button("Check", type="primary"):
    with st.spinner("Understanding…"):
        raw = llm.map_description(text, items, age_entry["label"], data["repetitive_behaviors"])
    rep = raw.get("repetitive", []) if isinstance(raw.get("repetitive"), list) else []
    ss.mapped = core.validate_mapping(raw, items)
    ss.repetitive = sorted({i for i in rep if isinstance(i, int) and 0 <= i < len(data["repetitive_behaviors"])})
    ss.llm_failed = not raw
    ss.checked_age = age
    ss.run += 1
    ss.pop("result", None)

if "mapped" not in ss:
    st.stop()

run, mapped = ss.run, ss.mapped
choices = ["Yes", "No", "Not sure"]
answers = {}

if ss.llm_failed:
    st.warning("We could not read the description automatically. Please answer the questions below.")

if mapped:
    st.subheader("What we understood")
    for item in items:
        m = mapped.get(item["id"])
        if not m:
            continue
        st.markdown(f"{EMOJI[m['status']]} **{question(item)}**")
        if m["quote"]:
            st.caption(f"“{m['quote']}”")
        pick = st.radio("Change", choices, index=choices.index(to_choice(item, m["status"])),
                        horizontal=True, key=f"m_{run}_{item['id']}", label_visibility="collapsed")
        answers[item["id"]] = to_status(item, pick)

# Step 4: follow-up for unmapped items
universal_ids = {u["id"] for u in data["universal_checks"]}
unmapped = [i for i in items if i["id"] not in mapped]


def rank(i):
    if i["id"] in universal_ids or i.get("autism_sign"):
        return 0
    return {"social_emotional": 1, "language_communication": 2}.get(i.get("domain"), 3)


main_qs = sorted([i for i in unmapped if rank(i) < 3], key=rank)
more_qs = [i for i in unmapped if rank(i) == 3]
follow = ["Skip"] + choices


def ask(item):
    pick = st.radio(question(item), follow, index=0, horizontal=True, key=f"f_{run}_{item['id']}")
    answers[item["id"]] = to_status(item, pick)


if unmapped:
    st.subheader("A few more questions")
    for item in main_qs:
        ask(item)
    if more_qs:
        with st.expander("More questions (optional)"):
            for item in more_qs:
                ask(item)

answers = {k: v for k, v in answers.items() if v}

# Step 5: result
if st.button("See result", type="primary"):
    ss.result = core.score(items, answers)
    ss.answers = answers

if "result" in ss:
    result = ss.result
    colour, msg = BANNER[result["level"]]
    st.markdown(
        f"<div style='background:{colour};color:white;padding:1.2rem;border-radius:0.6rem;"
        f"font-size:1.3rem;font-weight:600'>{msg}</div>",
        unsafe_allow_html=True,
    )
    st.info(data["act_early_rule"])
    for r in result["reasons"]:
        st.markdown(f"- {r}")
    quotes = {k: v["quote"] for k, v in mapped.items() if v["quote"]}
    repetitive = [data["repetitive_behaviors"][i] for i in ss.repetitive]
    note = core.doctor_note(age, age_entry, items, ss.answers, quotes, result, repetitive)
    st.download_button("Download note for the doctor (.md)", note,
                       file_name="mulai_doctor_note.md", mime="text/markdown")
