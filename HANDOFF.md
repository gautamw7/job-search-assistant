# Job Search Assistant — Handoff Document

## Project Overview
Single-user desktop app (Tauri + React) that enriches LinkedIn profiles via BrightData, generates personalized outreach messages using Gemini AI, supports multi-turn regeneration, and maintains full generation history. User brings their own API keys (BrightData, Gemini), runs entirely locally.

**Stack**: FastAPI (Python) + React/Vite/Tailwind/Shadcn (TS) + Tauri (Rust)
**Status**: Phase 1 functional — backend tested (20/20), frontend builds, Tauri dev runs, sidecar spawns backend.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Tauri Desktop  │────▶│  Vite Dev Server │────▶│  FastAPI :8000  │
│  (React UI)     │     │  (port 3000)     │     │  (Uvicorn)      │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┼───────────────────────────┐
                              ▼                           ▼                           ▼
                       ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
                       │ BrightData    │           │ Gemini AI     │           │ Local Storage │
                       │ (enrichment)  │           │ (generation)  │           │ (JSON/SQLite) │
                       └───────────────┘           └───────────────┘           └───────────────┘
```

**Single-User Model**: Local-first, user brings own API keys. No auth, no cloud sync. All data stored locally (JSON → SQLite). Distributable via `cargo tauri build` → signed binaries.

---

## Key Files

| Area | Path |
|------|------|
| Backend API | `api/main.py`, `api/routers/` |
| Services | `services/generator.py`, `services/enrich.py`, `services/resume.py` |
| Frontend | `frontend/src/App.tsx` (single-file, ~900 lines) |
| Tauri | `src-tauri/src/main.rs`, `src-tauri/tauri.conf.json` |
| Data | `data/generated_messages.json`, `data/user_communication_style.json`, `data/resume.md` |
| Prompts | `prompts/user_communication.yaml`, `prompts/regeneration_prompt.yaml` |

---

## What Works

- ✅ Resume upload (PDF → Markdown via pymupdf4llm)
- ✅ Communication style config (stored, retrieved, updated)
- ✅ Batch generation: multi-URL + notes → `POST /messages/batch`
- ✅ Regeneration: tweak input → `POST /messages/regenerate` (preserves context)
- ✅ Generation history: append-only, versioned per URL
- ✅ Master-Detail UI: Card A/B/C tabs + active card workspace
- ✅ Live progress: 3-stage pipeline + elapsed timer during generation
- ✅ Tauri sidecar: spawns uvicorn on startup, kills on window close
- ✅ Health check polling: `/health` with retry + status messages
- ✅ Error handling: per-card retry, specific error messages

---

## Clarifications & Decisions

### 1. CoT (Chain-of-Thought) Usage
**Where**: In the generation prompt (`prompts/regeneration_prompt.yaml` and initial generation prompt).
**How**: Model outputs structured analysis before the message:
```json
{
  "analysis": {
    "talking_points": ["specific skill match", "company context", "mutual connection"],
    "angle": "why this outreach makes sense",
    "grounding_check": ["name used", "company used", "specific detail from profile"]
  },
  "message": "Hey Marc, saw your post about hiring..."
}
```
Forces model to think/ground before writing.

### 2. History Purpose (Single User)
Not for "sent vs draft" status. Instead:
- **Eval dataset**: Every generation = training data for prompt iteration
- **Regression testing**: Re-run golden profiles after prompt changes
- **User memory**: "What did I send this person last time?"
- **Version comparison**: Side-by-side v1 vs v2 vs v3

No status field needed. Just: `id, version, linkedin_url, name, company, message, user_note, preferences, created_at`.

### 3. RAG/Vector Search
**Not needed for Phase 1**. Only for Phase 2 (connections.json):
- Embed all connections + ideal target profile → cosine similarity → top-K
- LLM rerank with reasoning
- Current enrichment (BrightData) provides structured fields — sufficient for single-profile generation.

### 4. Evaluation Harness
**Design**:
```
eval/
  golden_set.jsonl    # 20-30 {"profile": {...}, "ideal_message": "..."} pairs
  run_eval.py         # CLI: loads golden set, runs generation, scores
  metrics.py          # BLEU, ROUGE, custom "grounding score" (name/company present?)
```
**Grounding score**: Regex check for `name` and `company` in generated message.
**Run**: `python eval/run_eval.py --model gemini-1.5-flash` → outputs pass rate, avg latency, grounding %.

### 5. Enrichment → Grounding Fix
BrightData returns structured: `name`, `company`, `title`, `location`, `skills[]`, `posts[]`.
**Action**: Pass these as explicit fields to prompt (not raw JSON). Prompt template:
```
Recipient: {name} ({title} at {company})
Location: {location}
Skills: {skills}
Recent posts: {posts_summary}
```
Then add grounding checklist in CoT (see #1).

### 6. Fixture Files (Mock Mode)
```
fixtures/
  enrich_profile.json      # Sample BrightData response for one profile
  enrich_batch.json        # Sample batch response
```
Used when no BrightData key configured. `services/enrich.py` checks env var → if missing, returns fixture.

### 7. SQLite Migration
**Deferred** — schema still evolving. Keep JSON for now. Migration when:
- History table UI built (TanStack Table)
- Eval harness needs queryable history
- Schema stable for 1+ weeks

---

## Known Gaps (Phase 1 Completion)

| Priority | Issue |
|----------|-------|
| **P0** | Keyring integration (OS keyring via Rust `keyring` crate) |
| **P0** | Mock mode (fixture files for zero-key startup) |
| **P0** | Settings UI tab ("API Keys" with test connection) |
| **P0** | Fallback model chain (Gemini → Groq Gemma2 → Groq Llama3.1) |
| **P0** | Prompt upgrade: grounding checklist + 3 few-shot + CoT |
| **P1** | Eval harness (golden set + CLI runner) |
| **P1** | Enrichment fields passed explicitly to prompt |
| **P2** | SQLite migration (later) |

---

## Today's Plan (User)

1. **Endpoint for API keys intake** — `POST /config/keys`, `GET /config/keys` (masked)
2. **Regeneration context** — include `user_resume` + `communication_style` in regen call
3. **Fallback models** — config-driven chain: Gemini → Groq Gemma2 → Groq Llama3.1
4. **Few-shot examples** — add 3 golden (profile, message) pairs to system prompt
5. **ID + version** — add `id` (UUID) and `version` (int) to each generation record
5. **Research evaluation** — design golden set format + metrics

---

## Commands

```bash
# Backend
make run              # uvicorn on :8000
make test             # pytest (20 passing)

# Frontend
cd frontend && npm run build
cd frontend && npm run dev

# Tauri
make tauri-dev        # builds frontend, runs cargo tauri dev
```

---

## Phase 2 Vision (Connections)

- Input: `connections.json` (LinkedIn export)
- Embed connections + ideal target profile → cosine similarity → top-K
- LLM rerank: "Score 1-10 for outreach relevance. Explain why."
- Output: ranked table with reasoning, one-click generate

---

## Phase 3 Vision (Posts/Jobs)

- Monitor connections' posts for hiring signals
- Or: scrape company career pages / job boards
- Match against resume → auto-generate tailored applications

---

## Resume Context (for prompt tuning)

- **Role**: Data Scientist / Engineer Intern @ Syngenta (Feb–Aug 2026)
- **Core**: ML pipelines (XGBoost, TF/Keras), RAG (Gemini, Sentence Transformers, FAISS/Qdrant), Data Eng (Pandas, ETL, AWS S3/Glue/Redshift/SageMaker)
- **Achievements**: $75M/day decision framework, $6M SOOR reduction, 85 transfer flips detected, $33K license savings
- **Style**: Direct, concise, technical, "Hey [Name]" greeting, <100 words
