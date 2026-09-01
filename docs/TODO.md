# Job Search Assistant - Project Roadmap & Backlog

## 🚀 Active V1 Scope (In Progress)
- [x] Create modular core services (`services/parser.py`, `services/generator.py`, `services/resume.py`, `services/enrich.py`, `services/resources.py`)
- [x] Decouple backend with FastAPI routers (`api/main.py`, `api/routers/resume.py`, `api/routers/generate.py`)
- [x] **Dynamic V1 SPA Frontend (`frontend/index.html`)**:
  - [x] **View 1: Onboarding**: Drag-and-drop resume PDF upload and communication style saver.
  - [x] **View 2: Intake**: Target LinkedIn URL input + instant preference quick-interview.
  - [x] **View 3: Split-Pane Workspace**: Left Panel (Controls & overrides) + Right Panel (Draft with Copy-to-Clipboard + Enriched Recipient Data viewer).
- [ ] Align FastAPI endpoints with the SPA's stateless data contracts (Managed by user)

---

## 🅿️ Parked / Backlog Ideas (Post-V1 / Phase 2)
- [ ] **Local SQLite Database**:
  - Save generated message histories.
  - Build a persistent dashboard tab in the SPA UI to browse/search past outreach.
  - Native JSON caching of LinkedIn profiles.
- [ ] **Advanced Enrichment (NLP)**:
  - Intent classification on LinkedIn posts (Hiring vs. Culture vs. Events).
  - Graph grouping of `people_also_viewed` into GCCs and Agri-tech clusters.
- [ ] **Desktop Compiler**: Package the FastAPI server as a Python sidecar within a native Tauri 2 app wrapper.
