# Job suggestions and tailored resume — agreed design

Agreed in a design session on 2026-11-08. Delivered in four phases, one branch each.

## Who it is for
Works from any resume; defaults are derived from it and editable. The target user's
situation is first-class: India + Germany, entry level, data/ML, startups preferred,
visa sponsorship needed, German level taken into account.

## Search profile
The LLM reads the structured resume and proposes 3–5 titles, seniority, skills, ranked
target countries, company type, visa need, languages with levels, relocation/remote,
optional minimum salary and a one-line career direction, plus at most 3 clarifying
questions. The user confirms it in a pre-filled form. It is stored until edited or the
resume changes.

## Sources
- **Adzuna** (free). Search returns only a description snippet; must show an "Adzuna"
  link on each displayed job (terms of service). Supports `de` and `in`.
- **Apify** `curious_coder/linkedin-jobs-scraper` (~$1 per 1,000 results; full
  description, company employee count, applicants, seniority). Behind an adapter
  interface so more actors can be added. Sync run endpoint waits at most 300 s.
- On demand only ("Find jobs"); ≤ 3 titles × all target countries; last 30 days;
  ≤ 50 Apify results per search; 24 h cache; dedupe by company + title + city.

## Ranking (hybrid)
1. Gemini embeddings (`gemini-embedding-2`, 768 dims) narrow to the top ~50.
2. Weighted score: description similarity, title match, seniority, location/remote fit,
   skills overlap, recency, startup fit. Breakdown shown per job.
3. For the top 15: fetch full descriptions where only a snippet exists, then an LLM
   re-rank gives fit 0–100, reasons, missing skills, "German required" and
   "sponsorship mentioned".
- Startup: < 200 employees (Apify headcount) = verified; Adzuna = LLM guess, marked
  unverified. Germany realities: badges + score penalties; optional strict
  "hide German-required" filter.

## Jobs tab
Ranked list with filters; statuses new / saved / applied / dismissed (dismissed never
return). Each job: Tailor resume · People at this company (from the Tracker) · Write
outreach about this role.

## Tailored resume
- Source of truth: the structured base resume (one-time LLM conversion, user-reviewed).
- May only reorder, select and reword existing content; the fact checker compares the
  tailored version against the base resume and flags anything new.
- Structured data fills a fixed ATS-friendly LaTeX template (the LLM never writes raw
  LaTeX). Compile with system TeX Live if present, else bundled Tectonic (needs internet
  once for packages). The `.tex` is always downloadable.

## Storage
SQLite (`DATA_DIR/app.db`) with numbered SQL migrations in `app/db/migrations` and the
schema version in `PRAGMA user_version`; backed up before every upgrade. New data first;
existing JSON stores move in phase 4 with backups.

## Costs
"Free tier assumed" everywhere until the user enters prices. Adzuna, Apify and embedding
usage go into the usage ledger with monthly limits. Gemini 429s retry briefly; Apify
running out of credit skips that source and keeps Adzuna results. Free-tier Gemini
models are tried first.

## Phases
1. **Foundation** — SQLite + migrations, structured resume (convert / review / edit),
   Adzuna and Apify keys, model reorder.
2. **Job search** — profile + clarifying questions, sources, dedupe, embeddings,
   scoring, LLM re-rank with badges, Jobs tab, statuses.
3. **Tailored resume** — tailoring rules + fact check, LaTeX template, compile, PDF
   preview/download, links to outreach.
4. **Existing data → SQLite** — history, tracker, enrich cache, usage; JSON import with
   backups.

## Deferred
Cover letters, application autofill, scheduled background searches, more Apify actors
(Indeed, Naukri), importing a custom LaTeX template.
