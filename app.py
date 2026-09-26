import re

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
MAX_VIDEO_MB = 20
VIDEO_MIME = {"mp4": "video/mp4", "mov": "video/mov", "webm": "video/webm"}
VERDICT = {
    "confirmed": ("✅", "green", "Matches your answer"),
    "video_shows_skill": ("🔵", "blue", "Video shows this skill"),
    "worth_watching": ("👀", "orange", "Worth watching"),
    "consistent_concern": ("🔴", "red", "Matches your concern"),
}
LABEL = {"observed": "Yes", "not_observed": "No", "unclear": "Not sure", "not_assessed": "Not answered"}


def safe(text):
    """Model text: drop condition names and neutralise markdown/HTML."""
    return re.sub(r"([\\`*_\[\]()#!|~<>])", r"\\\1", core.sanitize(text))


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
        key = f"m_{run}_{item['id']}"
        ss.setdefault(key, to_choice(item, m["status"]))
        pick = st.radio("Change", choices, horizontal=True, key=key, label_visibility="collapsed")
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
    key = f"f_{run}_{item['id']}"
    ss.setdefault(key, "Skip")
    pick = st.radio(question(item), follow, horizontal=True, key=key)
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

# Step 4b: optional home video
by_id = {i["id"]: i for i in items}


def use_video(item_id, status):
    key = f"{'m' if item_id in mapped else 'f'}_{run}_{item_id}"
    ss[key] = to_choice(by_id[item_id], status)
    ss.pop("result", None)


def seek(seconds):
    ss.video_start = seconds


st.subheader("Home video (optional)")
video_consent = st.checkbox(
    "I am the parent/guardian. I consent to this video being analysed by an AI service to describe my "
    "child's behaviour. It is not stored by Mulai and is deleted from the AI service right after analysis.")
video = st.file_uploader(f"Upload a short video of your child playing (max 60 s, max {MAX_VIDEO_MB} MB)",
                         type=list(VIDEO_MIME)) if video_consent else None
if video is not None and video.size > MAX_VIDEO_MB * 1024 * 1024:
    st.warning(f"This video is larger than {MAX_VIDEO_MB} MB. Please trim it to under a minute and try again.")
    video = None
video_id = (video.file_id, run) if video is not None else None
if ss.get("video_id") != video_id:
    for k in ("video_raw", "video_obs", "video_rep", "video_start"):
        ss.pop(k, None)
    ss.video_id = video_id

if video is not None:
    st.video(video.getvalue(), start_time=ss.get("video_start", 0))
    if st.button("Analyse video"):
        with st.spinner("Watching the video…"):
            mime = VIDEO_MIME.get(video.name.rsplit(".", 1)[-1].lower(), "video/mp4")
            raw = llm.analyse_video(video.getvalue(), mime, items, age_entry["label"],
                                    data["repetitive_behaviors"])
        reps = raw.get("repetitive_seen") if isinstance(raw.get("repetitive_seen"), list) else []
        ss.video_raw = raw
        ss.video_obs = core.validate_video(raw, items)
        ss.video_rep = [(r["timestamp"], data["repetitive_behaviors"][r["index"]]) for r in reps
                        if isinstance(r, dict) and isinstance(r.get("index"), int)
                        and 0 <= r["index"] < len(data["repetitive_behaviors"])
                        and isinstance(r.get("timestamp"), str) and core.TIMESTAMP_RE.match(r["timestamp"])]

if "video_raw" in ss:
    raw = ss.video_raw
    if raw.get("error"):
        st.warning("We could not analyse this video. Please try again, or try a different clip.")
        st.caption(safe(raw["error"])[:300])
    elif not raw.get("video_ok"):
        st.warning("We couldn't see your child clearly in this clip. Please record a better one "
                   "with your child as the main subject.")
        if raw.get("quality_note"):
            st.caption(safe(raw["quality_note"]))
    else:
        st.markdown("#### Parent vs Video")
        if raw.get("summary"):
            st.caption(safe(raw["summary"]))
        if raw.get("quality_note"):
            st.caption("Video quality: " + safe(raw["quality_note"]))
        rows = core.compare(answers, ss.video_obs)
        if not rows:
            st.info("The video didn't clearly show any of the checklist behaviours. That is normal for a short clip.")
        widths = [3, 1.2, 1.3, 3]
        for col, head in zip(st.columns(widths), ["Milestone", "You said", "Video shows (mm:ss)", "Verdict"]):
            col.markdown(f"**{head}**")
        for r in sorted(rows, key=lambda r: core.ts_seconds(r["timestamp"])):
            emoji, colour, label = VERDICT[r["verdict"]]
            c1, c2, c3, c4 = st.columns(widths)
            c1.markdown(r["text"])
            c2.markdown(LABEL[r["parent"]])
            c3.button(f"▶ {r['timestamp']}", key=f"seek_{r['id']}", on_click=seek,
                      args=(core.ts_seconds(r["timestamp"]),))
            c4.markdown(f"{emoji} :{colour}[**{label}**]")
            if r["description"]:
                c4.caption(safe(r["description"]))
            if r["verdict"] == "video_shows_skill":
                c4.caption(f"The video shows this at {r['timestamp']}. You may want to update your answer.")
                c4.button("Use this", key=f"use_{r['id']}", on_click=use_video, args=(r["id"], "observed"))
            elif r["verdict"] == "worth_watching":
                c4.caption(f"In this clip there was a chance at {r['timestamp']} and it didn't happen. "
                           "One clip isn't enough; try again or mention it to the doctor.")
            elif r["verdict"] == "consistent_concern":
                c4.button("Use this", key=f"use_{r['id']}", on_click=use_video, args=(r["id"], "not_observed"),
                          disabled=r["parent"] == "not_observed")
        for ts, behaviour in ss.video_rep:
            st.caption(f"{ts} · Repetitive behaviour seen: {behaviour} (not scored)")

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
    video_ok = "video_raw" in ss and ss.video_raw.get("video_ok") and not ss.video_raw.get("error")
    note = core.doctor_note(age, age_entry, items, ss.answers, quotes, result, repetitive,
                            core.compare(ss.answers, ss.video_obs) if video_ok else None,
                            ss.video_rep if video_ok else None)
    st.download_button("Download note for the doctor (.md)", note,
                       file_name="mulai_doctor_note.md", mime="text/markdown")
