import html
import re
import time

import streamlit as st

import core
import llm
import viz

st.set_page_config(page_title="Mulai – early signs check", page_icon="🌱")

REGRESSION_Q = "Has your child stopped doing something they used to do (words, gestures, play)?"
# Every parent-facing Tamil string, in spoken Chennai Tamil, in one place for proofreading.
# viz.py gets its labels from here via arguments (importing app.py would run the whole Streamlit page).
TA = {
    "app_name": "முளை",
    "tagline": "குழந்தையோட வளர்ச்சி அடையாளங்கள முன்னாடியே கவனிப்போம்",
    "describe_label": "உங்க குழந்தையப் பத்தி சொல்லுங்க",
    "describe_hint": "பேர் சொல்லிக் கூப்பிட்டா திரும்பிப் பாக்குதா? விரல் நீட்டிக் காட்டுதா? என்ன வார்த்தைங்க பேசுது? "
                     "மத்த குழந்தைங்களோட விளையாடுதா? நீங்க செய்யறதப் பாத்து அதே மாதிரி செய்யுதா?",
    "yes": "ஆம்",
    "no": "இல்லை",
    "not_sure": "தெரியல",
    "regression_q": "முன்னாடி செஞ்சுக்கிட்டு இருந்த ஏதாவது ஒண்ண (வார்த்தைங்க, சைகைங்க, விளையாட்டு) "
                    "இப்போ செய்யறத நிறுத்திடுச்சா?",
    "branch_social": "பழகுறது",
    "branch_language": "பேச்சு",
    "branch_thinking": "யோசிக்கிறது",
    "branch_movement": "அசைவு",
    "act_u_name": "விளையாடிட்டு இருக்கும்போது பின்னாடி நின்னு, சாதாரண குரல்ல ஒரு தடவ பேர் சொல்லிக் கூப்பிடுங்க. "
                  "திரும்பிப் பாத்துச்சா?",
    "act_u_eye": "எதிர்ல உக்காந்து அதுக்குப் புடிச்ச சின்ன பாட்டு ஒண்ணு பாடுங்க. பாடும்போது உங்க முகத்தப் பாத்துச்சா?",
    "act_m12_se1": "கண்ணாமூச்சி இல்லன்னா கைதட்டி விளையாடுங்க. கூட சேர்ந்து விளையாடுச்சா, இன்னும் வேணும்னு கேட்டுச்சா?",
    "act_m12_lc1": "'டாட்டா'ன்னு சொல்லிக் கை ஆட்டுங்க. திருப்பிக் கை ஆட்டுச்சா?",
    "act_m15_se2": "புது பொம்மைய பக்கத்துல வைங்க. அத உங்ககிட்ட கொண்டு வந்துச்சா, இல்லன்னா தூக்கிக் காட்டுச்சா?",
    "act_m18_se2": "சுவாரஸ்யமா ஏதாவது ஒண்ணப் (பறவை, ஃபேன்) பாத்து 'வாவ், பாரு!'ன்னு சொல்லுங்க. "
                   "அத விரல் நீட்டிக் காட்டுச்சா?",
    "act_m24_se1": "கையில அடிபட்ட மாதிரி நடிச்சு, சோகமான முகத்தோட 'ஆ'ன்னு சொல்லுங்க. "
                   "நின்னு பாத்துச்சா, இல்லன்னா பக்கத்துல வந்துச்சா?",
    "act_m36_se2": "பார்க்ல இல்லன்னா சொந்தக்காரங்க குழந்தைங்களோட இருக்கும்போது, "
                   "மத்த குழந்தைங்ககிட்ட போய் சேர்ந்து விளையாடுச்சா?",
}
CARD_BUTTONS = [(f"{TA['yes']} Yes", "Yes"), (f"{TA['no']} No", "No"), (f"{TA['not_sure']} Not sure", "Not sure")]
BRANCH_TA = {k: TA[f"branch_{k}"] for k in ("social", "language", "thinking", "movement")}
LEGEND_TA = {k: TA[k] for k in ("yes", "no", "not_sure")}
# id -> (English, timed). Tamil text is TA[f"act_{id}"].
ACTIVITIES = {
    "u_name": ("While your child is playing, stand behind them and call their name once in a normal voice. "
               "Did they turn to look at you?", True),
    "u_eye": ("Sit face to face and sing a short song they like. Did they look at your face during the song?", True),
    "m12_se1": ("Play peek-a-boo or pat-a-cake. Did they join in or ask for more?", True),
    "m12_lc1": ("Wave bye-bye and say 'bye-bye'. Did they wave back?", True),
    "m15_se2": ("Put a new toy near them. Did they bring it or hold it up to show you?", True),
    "m18_se2": ("Look at something interesting (a bird, a fan) and say 'wow, look!'. "
                "Did they point to it or show you something themselves?", True),
    "m24_se1": ("Pretend to bump your hand and say 'ouch' with a sad face. Did they stop, look at you or come to you?",
                True),
    "m36_se2": ("At a park or with cousins, did they go near other children and join their play?", False),
}
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


st.title(f"{TA['app_name']} · Mulai")
st.write(f"{TA['tagline']} · Notice your child's early developmental signs, early.")

data = core.load_data()
_missing = sorted(set(ACTIVITIES) - core.all_ids(data))
if _missing:  # fail loudly: an activity for an id that doesn't exist would silently never show
    raise RuntimeError(f"ACTIVITIES ids not found in milestones.json: {_missing}")

# Step 1: consent
consent = st.checkbox("I am the child's parent/guardian and I agree to this check. "
                      "No name is collected. Nothing is stored after I close this page.")
st.caption("Consent as per DPDP Act 2023, Sec. 9")
if not consent:
    st.stop()

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
    f"Tell us about your child · {TA['describe_label']}",
    placeholder=f"{TA['describe_hint']}\n"
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
    ss.parent_text = text
    ss.run += 1
    ss.fu, ss.fu_idx, ss.fu_optional, ss.activity, ss.key_only = {}, 0, None, None, False
    ss.pop("result", None)

if "mapped" not in ss:
    st.stop()

run, mapped = ss.run, ss.mapped
by_id = {i["id"]: i for i in items}
choices = ["Yes", "No", "Not sure"]

if ss.llm_failed:
    st.warning("We could not read the description automatically. Please answer the questions below.")

# Current answers: reviewed AI mappings (radio state) + card answers
for item_id, m in mapped.items():
    ss.setdefault(f"m_{run}_{item_id}", to_choice(by_id[item_id], m["status"]))
answers = {i: to_status(by_id[i], ss[f"m_{run}_{i}"]) for i in mapped}
answers.update(ss.fu)
answers = {k: v for k, v in answers.items() if v}

video_ok = "video_raw" in ss and ss.video_raw.get("video_ok") and not ss.video_raw.get("error")
video_ids = {o["id"] for o in ss.video_obs} if video_ok else set()


def show_sprout(shown, width, flag):
    """Animate only the first time this sprout (screen or result) renders in the session."""
    animate = not ss.get(flag)
    ss[flag] = True
    # st.html strips <svg>; markdown keeps it. Safe because viz escapes every piece of text.
    st.markdown(viz.sprout_svg(items, shown, video_ids, width, BRANCH_TA, animate)
                + viz.legend_html(bool(video_ids), LEGEND_TA), unsafe_allow_html=True)


if mapped:
    st.subheader("What we understood")
    st.markdown("**What we heard → what it means**")
    st.html(viz.highlight_html(ss.parent_text, mapped, items))
show_sprout(answers, 520, "sprout_grown")
if mapped:
    for item in items:
        m = mapped.get(item["id"])
        if not m:
            continue
        st.markdown(f"{EMOJI[m['status']]} **{question(item)}**")
        if m["quote"]:
            st.caption(f"“{m['quote']}”")
        st.radio("Change", choices, horizontal=True, key=f"m_{run}_{item['id']}", label_visibility="collapsed")

# Step 4: follow-up question cards for unmapped items
universal_ids = {u["id"] for u in data["universal_checks"]}
unmapped = [i for i in items if i["id"] not in mapped]


def rank(i):
    if i["id"] in universal_ids or i.get("autism_sign"):
        return 0
    return {"social_emotional": 1, "language_communication": 2}.get(i.get("domain"), 3)


main_qs = sorted([i for i in unmapped if rank(i) < 3], key=rank)
more_qs = [i for i in unmapped if rank(i) == 3]
missing_key = sorted([i for i in items if core.is_key(i) and i["id"] not in answers], key=rank)

# "Skip to result" goes to the unanswered key questions first; a result only once they're answered.
if ss.pop("skip_requested", False):
    if missing_key:
        ss.key_only, ss.key_total, ss.activity = True, len(missing_key), None
    else:
        ss.want_result = True
if ss.get("key_only") and not missing_key and not ss.activity:
    ss.key_only = False
    ss.want_result = True
queue = missing_key if ss.get("key_only") else main_qs + (more_qs if ss.fu_optional else [])


def answer_card(item_id, choice):
    ss.fu[item_id] = to_status(by_id[item_id], choice)
    ss.pop("result", None)
    if choice == "Not sure" and item_id in ACTIVITIES:
        ss.activity = item_id
    else:
        ss.fu_idx += 1


def finish_activity(item_id, status):
    if status:
        ss.fu[item_id] = status
        ss.pop("result", None)
    ss.activity = None
    ss.fu_idx += 1


def go_back():
    ss.activity = None
    ss.fu_idx = max(0, ss.fu_idx - 1)


def set_optional(value):
    ss.fu_optional = value


def skip_to_result():
    ss.skip_requested = True


def answer_inline(item_id, choice):
    ss.fu[item_id] = to_status(by_id[item_id], choice)
    ss.want_result = True


def card_text(item):
    if item.get("is_regression_check"):
        return TA["regression_q"], REGRESSION_Q
    return (item["ta"], item["text"]) if item.get("ta") else (item["text"], "")


def ask_card(item, key_prefix, on_click):
    st.html(card_html(*card_text(item)))
    for col, (label, choice) in zip(st.columns(3), CARD_BUTTONS):
        col.button(label, key=f"{key_prefix}_{item['id']}_{choice}", on_click=on_click, args=(item["id"], choice),
                   type="primary" if choice == "Yes" else "secondary", width="stretch")


def card_html(big, small):
    small_html = f'<div style="color:#78909c;font-size:.95rem;margin-top:6px">{html.escape(small)}</div>' if small else ""
    return ('<div style="border:1px solid rgba(124,179,66,.45);border-radius:14px;padding:22px 20px;'
            f'background:rgba(124,179,66,.07)"><div style="font-size:1.35rem;font-weight:600;line-height:1.5">'
            f"{html.escape(big)}</div>{small_html}</div>")


if unmapped:
    st.subheader("A few more questions")
    idx = min(ss.fu_idx, len(queue))
    if ss.activity:
        item_id = ss.activity
        en, timed = ACTIVITIES[item_id]
        st.caption("🧸 An at-home observation. Not a test.")
        st.html(card_html(TA[f"act_{item_id}"], en))
        c1, c2, c3 = st.columns(3)
        c1.button("They did it", key="act_yes", on_click=finish_activity, args=(item_id, "observed"),
                  type="primary", width="stretch")
        c2.button("They didn't", key="act_no", on_click=finish_activity, args=(item_id, "not_observed"),
                  width="stretch")
        c3.button("Keep 'Not sure'", key="act_skip", on_click=finish_activity, args=(item_id, None),
                  width="stretch")
        if timed and st.button("▶ Start 30-second timer"):
            bar = st.progress(0.0, text="30 s")
            for sec in range(1, 31):
                time.sleep(1)
                bar.progress(sec / 30, text=f"{30 - sec} s" if sec < 30 else "Time's up. What happened?")
    elif ss.get("key_only"):
        done = ss.key_total - len(queue)
        st.progress(done / ss.key_total, text=f"Key question {done + 1} of {ss.key_total}")
        st.caption("We need these key questions before we can show a result.")
        ask_card(queue[0], "card", answer_card)
    elif idx < len(queue):
        item = queue[idx]
        st.progress(idx / len(queue), text=f"Question {idx + 1} of {len(queue)}")
        ask_card(item, "card", answer_card)
        prev = ss.fu.get(item["id"])
        if prev:
            st.caption(f"Your answer: {to_choice(item, prev)}")
    elif more_qs and ss.fu_optional is None:
        st.progress(1.0, text=f"{len(queue)} of {len(queue)} done")
        st.markdown(f"**Continue with optional questions?** ({len(more_qs)} more about thinking and movement)")
        c1, c2 = st.columns(2)
        c1.button("Yes, continue", on_click=set_optional, args=(True,), width="stretch")
        c2.button("No, that's enough", on_click=set_optional, args=(False,), width="stretch")
    else:
        st.progress(1.0, text="All questions answered")
        st.success("Thank you. Press “See result” below.")
    b1, b2 = st.columns(2)
    if (idx > 0 or ss.activity) and not ss.get("key_only"):
        b1.button("← Back", on_click=go_back)
    if not ss.get("key_only"):
        b2.button("Skip to result →", on_click=skip_to_result)

# Step 4b: optional home video


def use_video(item_id, status):
    if item_id in mapped:
        ss[f"m_{run}_{item_id}"] = to_choice(by_id[item_id], status)
    else:
        ss.fu[item_id] = status
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
        st.rerun()  # redraw the sprout above with "seen in video" rings

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
if st.button("See result", type="primary") or ss.pop("want_result", False):
    ss.result = core.score(items, answers)
    ss.answers = answers

if "result" in ss and ss.result["level"] == "INCOMPLETE":
    result = ss.result
    msg = ("Not enough answers yet. Please answer these key questions." if result["missing_key"] else
           f"Not enough answers yet. Please answer at least {result['more_needed']} more of these questions.")
    st.markdown(f"<div style='background:#607d8b;color:white;padding:1.2rem;border-radius:0.6rem;"
                f"font-size:1.3rem;font-weight:600'>{msg}</div>", unsafe_allow_html=True)
    pending = result["missing_key"] or sorted(result["not_assessed"], key=rank)
    for item in pending:
        ask_card(item, "inc", answer_inline)
elif "result" in ss:
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
    show_sprout(ss.answers, 680, "result_sprout_grown")
    quotes = {k: v["quote"] for k, v in mapped.items() if v["quote"]}
    repetitive = [data["repetitive_behaviors"][i] for i in ss.repetitive]
    note = core.doctor_note(age, age_entry, items, ss.answers, quotes, result, repetitive,
                            core.compare(ss.answers, ss.video_obs) if video_ok else None,
                            ss.video_rep if video_ok else None)
    st.download_button("Download note for the doctor (.md)", note,
                       file_name="mulai_doctor_note.md", mime="text/markdown")
