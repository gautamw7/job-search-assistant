# 7-Day Sprint Roadmap

## Goals
- **Phase 1 Done**: LinkedIn URL → Bright Data → Person → LLM Outreach → Saved Locally. Works without Google Sheets.
- **Phase 2 Done**: Connections CSV → Connections Table → Filter & Rank (Top 75) → Selected Connection → Phase 1 Outreach.
- **Application Done**: Package backend as a Tauri sidecar with React UI.

---

## Day-by-Day Plan

### Day 1: Groundwork & Contracts
- Define backend architecture (done).
- Establish project directory structure (done).
- Set up SQLite connection & SQLAlchemy models based on schema.
- Write mock services for Bright Data and LLM to enable rapid API prototyping.
- **Gate**: SQLite schema verified; DB migrations work; mock endpoints return expected schemas.

### Day 2: Phase 1 Backend Service
- Create FastAPI endpoints for `/api/v1/profile` and `/api/v1/enrich`.
- Refactor existing LinkedInHelper code:
  - Extract URL normalization/ID extraction logic.
  - Implement Bright Data dataset trigger & snapshot polling in a robust, async Service.
  - Integrate LiteLLM wrapper with fallback models pool for robust generation.
- **Gate**: CLI/cURL request with LinkedIn URL fetches profile via Bright Data, saves to `people`, generates and saves valid outreach draft to `outreach_messages`.

### Day 3: Secrets & Security
- Integrate Python `keyring` library for secrets management.
- Ensure API keys for Gemini, Claude, and Bright Data are stored in Keychain/Credential Manager.
- Store metadata (endpoints, provider configs) in SQLite `provider_config` table.
- Test fallback behavior if keys are missing from keyring.
- **Gate**: System runs successfully with keys retrieved from Keyring at runtime.

### Day 4: React UI Setup & Phase 1 Frontend
- Setup Vite + React + Tailwind CSS project inside `frontend/`.
- Build the User Profile setup screen (resume/profile Markdown editor).
- Build the "Reach Out" screen:
  - Input fields: LinkedIn URL, optional context.
  - Button to trigger enrichment.
  - Interactive "Review & Edit" drawer for the generated message (side-by-side: recipient details vs outreach message editor).
  - Copy to clipboard & Save buttons.
- **Gate**: User can fully configure profile, enter a URL, click generate, edit, and copy the message via the local browser UI.

### Day 5: Phase 2 Backend & Filtering
- Implement `/api/v2/connections/import` endpoint. Parse LinkedIn connections CSV and insert to `connections` table.
- Implement `/api/v2/connections/filtered` with cheap, local scoring & ranking algorithms (no API calls).
- Implement `/api/v2/connections/enrich-batch` (with user budget controls).
- **Gate**: Real LinkedIn connections CSV imported successfully, sorted by score, and enriched within budget constraints.

### Day 6: Phase 2 UI & Integration
- Build Phase 2 "My Network" screen:
  - CSV Import dropzone.
  - Ranked Connections Table (paginated/filtered). Show score, first/last name, current title/company, and enriched status.
  - Budget selector and "Enrich Top N" button.
  - Select connection row → open Phase 1 outreach drawer with prepopulated profile.
- Implement error handling dialogs (API timeouts, missing keys, invalid CSV).
- **Gate**: Full imported connection journey (Import → Filter → Enrich → Generate → Save/Copy) works seamlessly from the UI.

### Day 7: Packaging & Handoff
- Setup Tauri 2 shell in `src-tauri/`.
- Configure Tauri sidecar to launch the FastAPI backend on startup and stop on exit.
- Package app for the current host OS (Mac/Linux/Windows).
- Complete README, architecture diagrams, and known limitations documentation.
- **Gate**: Native app binary runs on double-click, opens UI, starts backend, and operates fully offline-first.

---

## Definition of Done (Sprint End)
- A non-technical person can install and use Phase 1 & Phase 2.
- Clean Git history with meaningful commits.
- Architecture and schema documented (done).
- No hardcoded API keys anywhere.
- SQLite persistence survives application restarts.
