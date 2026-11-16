# Smart Internship Match

Personal decision-support pipeline for my 6-month internship search: collect real
offers, structure them with a local LLM, score them against my own skills, draft
cover-letter openings for the best ones, track my applications and monitor the search.

**Private repository on purpose**: my skills profile and targeted offers are personal
data, and scraped offers (Indeed via jobspy) must never be redistributed. The
dashboard is therefore viewed locally, not on GitHub Pages.

## Pipeline

| Step | Script | Output | Committed? |
|---|---|---|---|
| Acquisition (Indeed, local) | `scripts/fetch_offers_jobspy.py` | `data/offers/jobspy_offers.json` + `data/pipeline/source_log.csv` | offers: no |
| Acquisition (France Travail) | not connected yet, API unavailable during the project | `data/offers/raw_offers.json` | - |
| Merge to a common schema | `scripts/merge_offer_sources.py` | `data/offers/merged_offers.json` | no |
| AI extraction (Ollama, `qwen3:8b`) | `scripts/extract_offers.py` | `data/offers/structured_offers.json` | no |
| Match KPI | `scripts/match_offers.py` | `data/offers/matches_all_local.json`, `docs/data/matches.json` (publishable only) | local file: no |
| Cover-letter openings | `scripts/draft_cv.py` | `output/cv_drafts/` | **never** |
| Monitoring | `scripts/monitor.py` | `data/monitoring/monitoring_log.csv` | yes |
| Dashboard | `docs/dashboard.html` | - | yes |

Hand-maintained files: `data/profile/my_skills.csv` (skills, level 1-5, evidence),
`data/tracker/applications.csv` (applications and answers),
`data/quality/extraction_review.csv` (AI errors found by re-reading the extraction).

## Run everything

Ollama must be running (`curl.exe --noproxy "*" http://127.0.0.1:11434/api/version`).

```
python -X utf8 scripts\fetch_offers_jobspy.py
python -X utf8 scripts\merge_offer_sources.py
python -X utf8 scripts\extract_offers.py
python -X utf8 scripts\match_offers.py
python -X utf8 scripts\draft_cv.py
python -X utf8 scripts\monitor.py
python -m http.server 8000
```

Then open http://localhost:8000/docs/dashboard.html.

## Match KPI (summary)

- coverage = matched / (matched + 1/3 x missing): a missing skill weighs 3x less than one I have
- score = 100 x coverage x (0.8 + 0.2 x average level / 5): level refines, never decides
- skill names compared after normalization, whole-word, plus a small synonym list
- offers with no extracted skill are set apart (`scorable: false`)
- ranking uses `priority` = score + 15 if the offer is in AI (my target domain), capped at 100
