# MilestoneAI

A Tamil/English early developmental-signs check for parents of children aged 12–71 months.
A parent describes their child in their own words, typed or spoken (Tamil, English or Tanglish). An AI maps the
description onto the CDC milestone checklist for the child's age. Plain Python rules, not the AI,
decide the result. The parent gets clear next steps, read aloud in Tamil, and a note to take to the doctor.

MilestoneAI never diagnoses and never names a condition.

## The problem

- About **1 in 100** Indian children aged 2–9 have autism. This comes from a population study of
  about 4,000 children across five regions; site estimates ranged from 0.4% to 1.8%
  (Arora et al., INCLEN, *PLOS Medicine*, 2018).
- In a Delhi study, parents' first concerns came **about 1.5 years before** the child's diagnosis.
  Lack of awareness of age-appropriate milestones, among families and health professionals, was a
  key reason (*Journal of Autism and Developmental Disorders*, 2022; published online 2021).

Early help works best when it starts early. MilestoneAI aims to shorten the time between "something
feels off" and "let's talk to the doctor".

## How it works

```
Parent's words: typed text and/or a voice recording
   │
   ▼
Gemini transcribes the voice and maps everything to milestone IDs
   │                                   ──►  whitelist: unknown IDs and statuses are dropped
   ▼
"What we heard": the parent's words (or transcript) with each matched phrase highlighted
   │
   ▼
Parent reviews what we understood, then answers the remaining questions as one-at-a-time cards
("Not sure" on key items opens a 30-second at-home activity)
   │
   ▼
Python rule engine scores:  RED / AMBER / GREEN / INCOMPLETE
   │
   ▼
Result banner + growing "sprout" of milestones + downloadable doctor note (.md)
   │
   ▼
Gemini writes a short Tamil explanation from the result only  ──►  safety filter
   │   (a condition name → fixed Tamil template instead)
   ▼
gTTS reads it aloud in Tamil
```

- **Rules (core.py):** any key sign not seen → RED; lost skills → RED; anything else not seen or
  "not sure" → AMBER. GREEN only when every key question is answered **and** at least 60% of the
  checklist is answered. Otherwise the result is INCOMPLETE and the app asks the missing key questions.
- **Optional home video:** Gemini lists timestamped observations for the same whitelisted IDs.
  The app shows where the video agrees or disagrees with the parent. The video never changes the
  score on its own; the parent confirms each suggestion with one tap.
- **Voice input:** the parent can record instead of typing. The recording goes to Gemini with the
  same mapping prompt, and Gemini also returns a transcript, which is shown under "What we heard"
  and used for the highlighting.
- **Tamil voice result:** Gemini writes 4–6 short, warm spoken-Tamil sentences using only the result
  (level, milestones not yet seen, what to do). RED and AMBER always say to see a doctor. If the text
  contains a condition name, or Gemini fails, a fixed Tamil template for that level is used instead.
  INCOMPLETE always uses its template ("please answer the key questions"). gTTS turns the text into
  audio; if that fails, the text is shown without audio.
- **Never crashes on a failed call:** every Gemini and gTTS call is wrapped. A failed mapping shows a
  warning and falls back to the manual questions; a failed voice result falls back to template text.
- **All Tamil in one place:** every parent-facing Tamil string is in the `TA` dict in `app.py`
  (spoken Chennai register) so a native speaker can proofread it in one pass.

## Privacy and security

- **Consent first:** nothing renders until a parent/guardian ticks consent. The parent sees exactly this:

  > I am the child's parent or guardian and I agree to this check. No name is collected. MilestoneAI saves nothing: when I close this page, my answers are gone. What I type or say is sent to Google's Gemini AI service to be understood, and the result explanation is sent to Google to be read aloud. Google may keep this data for a limited time under its own terms and, on the free tier, may use it to improve its services.

  The video has its own, separate consent:

  > I am the child's parent or guardian and I agree to this video being sent to Google's Gemini AI service to describe my child's behaviour. MilestoneAI does not save the video. Google may keep it for a limited time under its own terms and, on the free tier, may use it to improve its services.

- **No name collected. No database. Nothing written to disk.** State lives in the browser session
  and is gone when the page is closed.
- **Data does leave the device:** the description, voice recording or video goes to the Google Gemini
  API, and the Tamil result explanation goes to Google's text-to-speech service (gTTS). What Google
  keeps depends on the API tier (see Limitations).
- **Prompt injection can't change the score:** the model can only return IDs from the checklist
  whitelist and one of three fixed statuses; anything else is dropped (`validate_mapping`,
  `validate_video`). The parent's words are wrapped as data, and the score is computed by Python.
- **Output safety:** model text is filtered for condition names and escaped before display; all
  parent text is HTML-escaped before highlighting.
- **Secrets:** the API key lives in `.streamlit/secrets.toml`, which is git-ignored.

## Setup

```bash
pip install -r requirements.txt
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "your-key"' > .streamlit/secrets.toml   # never commit this file
streamlit run app.py
```

`milestones.json` (the CDC checklists) must be in the repo root. Run the tests with
`python test_core.py`. Check the demo scenarios against the live model with
`python demo/check_scenarios.py`; the scenario texts are in `demo/scenarios.md`.

## Limitations

- **Not clinically validated.** This is a hackathon prototype and a screening aid, not a
  screening instrument or a diagnosis. The 60% coverage threshold is a design choice, not a
  clinical cut-off.
- **CDC milestones are US-based** and have not been validated for Indian or Tamil-speaking
  children.
- **Gemini's free tier is not suitable for real child data:** Google may use free-tier inputs to
  improve its products, and human reviewers may read them. Even the paid tier keeps logs for abuse
  monitoring for a limited period. A real deployment needs a paid tier with appropriate data
  controls.
- AI mapping can be wrong: the parent reviews and can change every mapped answer. Video timestamps
  are approximate (the model samples frames), and one short clip is never evidence that a child
  can't do something.

## Credits

- Milestone content: CDC "Learn the Signs. Act Early."
- Google Gemini API, gTTS, Streamlit
- Built with AI coding assistance (Claude Code) during CYNEX 2K26, 26 Sep 2026.
