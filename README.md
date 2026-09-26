# முளை · Mulai

A Tamil/English early developmental-signs check for parents of children aged 12–71 months.
A parent describes their child in their own words (Tamil, English or Tanglish). An AI maps the
description onto the CDC milestone checklist for the child's age. Plain Python rules, not the AI,
decide the result. The parent gets clear next steps and a note to take to the doctor.

Mulai never diagnoses and never names a condition.

## The problem

- About **1 in 100** Indian children aged 2–9 have autism. This comes from a population study of
  about 4,000 children across five regions; site estimates ranged from 0.4% to 1.8%
  (Arora et al., INCLEN, *PLOS Medicine*, 2018).
- In a Delhi study, parents' first concerns came **about 1.5 years before** the child's diagnosis.
  Lack of awareness of age-appropriate milestones, among families and health professionals, was a
  key reason (*Journal of Autism and Developmental Disorders*, 2022; published online 2021).

Early help works best when it starts early. Mulai aims to shorten the time between "something
feels off" and "let's talk to the doctor".

## How it works

```
Parent's words (text)
   │
   ▼
Gemini maps them to milestone IDs  ──►  whitelist: unknown IDs and statuses are dropped
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
```

- **Rules (core.py):** any key sign not seen → RED; lost skills → RED; anything else not seen or
  "not sure" → AMBER. GREEN only when every key question is answered **and** at least 60% of the
  checklist is answered. Otherwise the result is INCOMPLETE and the app asks the missing key questions.
- **Optional home video:** Gemini lists timestamped observations for the same whitelisted IDs.
  The app shows where the video agrees or disagrees with the parent. The video never changes the
  score on its own; the parent confirms each suggestion with one tap.
- **Planned, not in this build:** a Tamil explanation of the result written by Gemini behind a
  safety filter, and read aloud with gTTS. (gTTS is in `requirements.txt` for that step.)

## Privacy and security

- **Consent first:** nothing renders until a parent/guardian ticks consent. The video has its own,
  separate consent.
- **No name collected. No database. Nothing written to disk.** State lives in the browser session
  and is gone when the page is closed.
- **Data does leave the device:** the description (and any video) is sent to the Google Gemini API
  for mapping. What Google keeps depends on the API tier (see Limitations).
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
