# Project Handoff — Open-Source Job Search Assistant

## 1. Project Status

**Current stage:** Planning / architecture checkpoint
**Sprint:** 7-day max-effort sprint
**Primary goal:** Ship a usable Phase 1 + Phase 2 desktop application that can be showcased publicly and defended in interviews.

This project is intentionally separate from the planned RSNA knee abnormality ML project. The Job Search Assistant is a short software/product engineering sprint, not the flagship core-ML project.

---

## 2. Why We Are Building It

The problem:

Modern job searching involves finding relevant people, understanding why they may be useful contacts, writing personalized outreach, tracking interactions, and following up. Doing this manually across spreadsheets and scripts is repetitive and difficult to maintain.

Core workflow:

```text
Find person → Understand relevance → Generate one good message → Review/edit → Save/track → Follow up
```

Second workflow:

```text
Import connections → Cheap local filtering → Select promising candidates
→ Enrich selectively → Rank → Identify high-impact contacts → Generate outreach
```

Phase 3 — job aggregation/tracking — is out of scope for this sprint.

### Product philosophy

Build the smallest genuinely useful open-source application.

The product should be:

- easy for another person to install and use
- local-first
- open-source
- API-cost conscious
- understandable
- modular
- testable
- presentable on GitHub
- showcaseable on LinkedIn

---

## 3. Sprint Definition of Success

### Outcome 1 — Someone else can use it

Phase 1:

```text
Install/open → Configure profile/resume → Reach Out
→ Enter LinkedIn URL → Enrich → Generate message
→ Review/edit → Save/copy
```

Phase 2:

```text
Import connections → Filter → Choose enrichment budget
→ Enrich selected candidates → Rank → Select person
→ Generate outreach
```

The user should not need to understand Python, FastAPI, React, virtual environments, or backend commands.

### Outcome 2 — Showcaseable and interview-defensible

The project should have:

- public GitHub repository
- clean README
- architecture diagram
- screenshots/demo
- clear setup instructions
- documented trade-offs
- known limitations
- meaningful Git history
- LinkedIn showcase material

The developer should be able to explain:

- why the architecture exists
- why local-first was chosen
- why SQLite was chosen
- why FastAPI was chosen
- why Tauri was chosen
- why Bright Data is used
- why enrichment is selective
- how LLM providers are abstracted
- how failures are handled
- how secrets are stored
- what would change at larger scale

### Outcome 3 — Learn something

The project should deliberately strengthen:

- backend/service architecture
- API design
- external API integration
- local persistence
- process lifecycle
- frontend/backend integration
- desktop packaging
- API failure handling
- testing
- configuration/secrets
- cost-aware pipeline design
- refactoring an existing POC into a maintainable system

At the end of the sprint, record:

```text
What I built:
What I learned:
Decision I made:
Alternative I rejected:
Why:
What broke:
What I would redesign:
```

---

## 4. Recommended Architecture

```text
                    DESKTOP APPLICATION
                           │
                      Tauri 2 Shell
                           │
             ┌─────────────┴─────────────┐
             │                           │
      React + TypeScript           FastAPI Backend
             │                           │
             │                    ┌──────┴──────┐
             │                    │             │
             │                  SQLite      Services
             │                                  │
             │                    ┌─────────────┼─────────────┐
             │                    │             │             │
             │               Bright Data      LLM        Local Logic
             │
             └──────────── HTTP ────────────────┘
```

### Responsibilities

**Tauri:** desktop shell, packaging, lifecycle, FastAPI/Python sidecar management.

**React + TypeScript:** UI, forms, loading/error states, profile/message/network views, settings.

**FastAPI:** API, validation, orchestration, persistence coordination, external APIs, LLM calls, filtering/ranking.

**SQLite:** local persistent data.

**Bright Data:** LinkedIn profile enrichment.

**LLM provider:** personalized outreach generation.

LiteLLM is the intended provider abstraction where useful.

Tauri is the delivery mechanism, not the core business logic.

---

## 5. Desktop Runtime Model

Intended runtime:

```text
User opens application
        ↓
Tauri starts
        ↓
Python/FastAPI sidecar starts
        ↓
FastAPI listens locally
        ↓
React UI loads
        ↓
React checks backend health
        ↓
Application ready
```

FastAPI remains a normal local HTTP server.

Conceptually:

```text
React
  ↓ HTTP
127.0.0.1:<port>
  ↓
FastAPI
  ↓
SQLite / external services
```

Shutdown:

```text
Tauri shutdown → FastAPI process terminates → Desktop application exits
```

The exact Tauri ↔ FastAPI process-management mechanism is **not yet decided**.

---

## 6. Development Order

Do not build Tauri first.

```text
1. Understand existing code
2. Define clean Phase 1 backend contract
3. Build/refactor Phase 1 backend
4. Add SQLite persistence
5. Build React UI
6. Build Phase 2
7. Integrate full workflow
8. Test failure cases
9. Package with Tauri
10. Document and ship
```

---

## 7. Existing Codebase

The existing implementation is a proof-of-concept / legacy Google Sheet workflow.

Current flow:

```text
Google Sheet
    ↓
Bright Data enrichment
    ↓
Resume parsing
    ↓
LLM message generation
    ↓
Google Sheet update
```

Existing useful functionality includes:

- LinkedIn URL normalization
- LinkedIn public ID extraction
- Bright Data dataset triggering
- snapshot polling
- profile parsing
- profile-to-text conversion
- resume PDF extraction
- personalized LLM outreach generation

The current Bright Data implementation is tightly coupled to DataFrames/Google Sheets and should be extracted into reusable services.

The current message generator contains candidate-specific professional context directly in the module. That must become user-configurable for an open-source application.

---

## 8. Legacy Google Sheets

The existing Google Sheet workflow is legacy.

**Do not modify it as part of the new application.**

The new application should not depend on Google service-account credentials, Google Sheets, or Google Drive for normal operation.

---

# 9. Phase 1 — Reach Out

## User input

Required:

- LinkedIn profile URL

Optional:

- user-provided context

Examples:

```text
We are VIT alumni.
I noticed their work in supply chain.
I want to understand their team.
```

User profile/context:

- resume
- target roles
- domains/interests
- career positioning
- outreach preferences

## Workflow

```text
LinkedIn URL
    ↓
Validate URL
    ↓
Bright Data enrichment
    ↓
Normalize profile
    ↓
Combine:
    user profile
    +
    resume
    +
    recipient profile
    +
    user context
    ↓
LLM
    ↓
Quality checks
    ↓
Generated message
    ↓
User review/edit
    ↓
Save/copy
```

Conceptual backend contract:

```text
Input:
    linkedin_url
    user_context
    user_profile

Output:
    structured_person
    generated_message
    metadata
```

Exact schemas are not decided yet.

### Phase 1 Definition of Done

A user can:

1. Open the application.
2. Configure their profile/resume.
3. Enter a LinkedIn URL.
4. Add optional context.
5. Enrich the profile through configured Bright Data.
6. Generate one personalized message using a configured LLM.
7. Review/edit it.
8. Copy/save it.
9. See the person persisted locally.

---

# 10. Phase 2 — My Network / High-Impact Connections

## Input

LinkedIn connection export:

- CSV
- JSON if available/supported

Known fields may include:

- first name
- last name
- URL
- email
- company
- position

## Workflow

```text
Connection export
    ↓
Import
    ↓
Normalize
    ↓
Cheap local/rule-based filtering
    ↓
Top N candidates
    ↓
Selective Bright Data enrichment
    ↓
Ranking
    ↓
Top 75 / configurable list
    ↓
User selects person
    ↓
Phase 1 outreach
```

## Critical constraint

Do not enrich every connection.

Bad:

```text
1,000 connections → 1,000 Bright Data calls
```

Preferred:

```text
1,000 connections
    ↓
cheap local filtering
    ↓
~100 candidates
    ↓
~100 enrichments
    ↓
ranking
    ↓
top 75
```

The enrichment limit must be configurable.

---

# 11. High-Impact Connection Definition

Not finalized.

Potential signals:

- target role relevance
- seniority
- target company
- industry/domain
- country/location
- similarity to career goals
- structured profile signals
- semantic relevance

Do not implement a complicated ranking algorithm before defining what “high-impact” means.

Do not introduce a vector database unless evidence shows that it is useful.

Start simple and add complexity only when it improves the actual result.

---

# 12. LLM Architecture

Provider-agnostic design.

Potential providers:

- Gemini
- Claude
- OpenAI
- OpenAI-compatible APIs

Configuration concept:

```text
Provider
Model
Base URL (optional)
API Key
Enabled
```

No personal hardcoded API keys.

User professional context must also not be hardcoded.

```text
User Profile
    ↓
Outreach Service
    ↓
Prompt Construction
    ↓
LLM Provider
```

### Message quality requirements

Messages should generally:

- be short
- sound human
- be professional without being corporate
- use reliable recipient-specific information
- avoid generic compliments
- avoid fake enthusiasm
- avoid fabricated facts
- avoid exaggerated claims
- avoid immediate referral requests
- make a small/easy networking ask
- be editable
- require human approval

---

# 13. Data Model — Initial Concept

Likely entities:

```text
UserProfile
Person
OutreachMessage
EnrichmentRecord
UserPreference
ProviderConfig
```

Potential future entity:

```text
Interaction
```

Do not finalize the schema before implementing the workflows.

---

# 14. Security

Never commit:

- API keys
- service-account credentials
- personal secrets
- user database
- private resumes

Development may use `.env` locally.

`.env.example` should contain variable names only.

For the packaged application, use an appropriate local secure secret-storage mechanism.

Exact secure-storage implementation is not yet decided.

---

# 15. Error Handling

Handle at least:

### Bright Data

- invalid URL
- enrichment failure
- profile not found
- timeout
- malformed response
- usage/rate limit

### LLM

- missing API key
- provider failure
- timeout
- malformed output
- empty output
- provider unavailable

### Import

- malformed CSV
- missing columns
- duplicate connections
- invalid LinkedIn URLs
- empty file

### Application

- missing resume
- database error
- backend unavailable
- unexpected frontend error

Normal users should not see raw stack traces.

---

# 16. Testing Strategy

## Unit tests

- LinkedIn URL parsing
- profile normalization
- connection normalization
- filtering
- ranking
- message validation
- configuration validation

## Integration tests

- Phase 1 service flow
- database persistence
- mocked Bright Data
- mocked LLM

External services should not be required for ordinary automated tests.

## Manual tests

Phase 1:

```text
Install/open → setup → Reach Out → enrich → generate → edit → save
```

Phase 2:

```text
Import → filter → enrich → rank → select → generate
```

---

# 17. Seven-Day Sprint

## Day 1 — Understand + Boundaries

- inspect complete project tree
- understand Google Sheet flow
- understand Bright Data flow
- understand resume parser
- understand message generator
- map current data flow
- identify coupling
- define Phase 1 service contract
- define architecture
- record open decisions

**Gate:** Explain every major component and why it exists.

## Day 2 — Phase 1 Backend

- create FastAPI application
- create service boundaries
- extract Bright Data integration
- extract profile normalization
- make user profile configurable
- integrate LLM provider abstraction
- create Phase 1 endpoint(s)
- validate output

**Gate:**

```text
LinkedIn URL → Bright Data → Person
Person + User Profile → LLM → validated message
```

works without Google Sheets.

## Day 3 — SQLite

- choose database library
- define minimum schema
- implement persistence
- save people
- save messages
- save user profile
- handle duplicates
- test restart persistence

**Gate:** Data survives application restart.

## Day 4 — React Phase 1

```text
Setup
 ↓
Resume/profile
 ↓
Reach Out
 ↓
LinkedIn URL
 ↓
Context
 ↓
Generate
 ↓
Review
 ↓
Edit
 ↓
Save / Copy
```

**Gate:** Non-technical person can use Phase 1 without developer assistance.

## Day 5 — Phase 2

- import CSV
- normalize
- validate
- deduplicate
- define cheap filtering
- define enrichment budget
- selective enrichment
- initial ranking
- ranked candidate UI

**Gate:** Real connection export produces a useful ranked list.

## Day 6 — Integration + Reliability

- Phase 2 → Phase 1
- API failures
- LLM failures
- Bright Data failures
- malformed CSV
- missing configuration
- duplicates
- loading states
- error states
- retry behavior where appropriate

**Gate:** Complete user journey works without developer intervention.

## Day 7 — Ship + Defend

- clean GitHub repository
- README
- architecture diagram
- screenshots/demo
- installation instructions
- configuration documentation
- known limitations
- tests
- demo
- LinkedIn showcase material
- package desktop application if core workflows are stable
- review decisions/trade-offs
- record lessons learned

---

# 18. Explicitly Out of Scope

- automatic LinkedIn messaging
- automatic applications
- job aggregation
- resume rewriting
- cover letters
- complex CRM
- social graph analysis
- vector database without demonstrated need
- multi-user cloud backend
- SaaS authentication
- billing
- perfect cross-platform packaging
- unnecessary analytics dashboards

Phase 3 — jobs — remains deferred.

---

# 19. Engineering Principles

### Do not rewrite everything

Preserve useful existing behavior.

### Do not blindly copy the POC

Understand current behavior before moving it.

### Do not over-engineer

Every component must justify its complexity.

### Do not add technology for resume keywords

Technology must solve a real requirement.

### Do not make Tauri the project

Tauri exists to provide a good distribution experience.

### Do not make the LLM the project

The product is the job-search/networking workflow.

### Do not optimize prematurely

First make the workflow correct and useful.

### Do not silently make major architectural decisions

Surface decisions that materially affect requirements, architecture, cost, security, or user behavior.

---

# 20. Current Open Decisions

These require explicit decisions:

- exact Tauri ↔ FastAPI process-management mechanism
- Python packaging/sidecar mechanism
- SQLite library/ORM
- React component/design system
- Bright Data endpoint/dataset configuration
- LLM provider implementation
- ranking algorithm
- definition of “high-impact connection”
- whether embeddings are needed
- secret-storage mechanism
- packaging/build pipeline
- cross-platform release strategy
- database schema
- API request/response contracts

Do not treat the proposed architecture as final until these are validated.

---

# 21. Questions Before Implementation

### Requirements

→ Who is the first external user?

→ What exactly makes a connection “high-impact”?

→ What is the maximum acceptable Bright Data enrichment budget for one run?

→ What information must a user provide before generating a message?

→ What information must Bright Data provide?

→ What should be persisted?

### Architecture

→ How should Tauri manage the FastAPI sidecar?

→ How should Tauri detect backend readiness?

→ How should FastAPI shut down?

→ How should the packaged Python runtime be distributed?

→ How should secrets be stored?

Research/document major decisions before implementation where necessary.

---

# 22. Suggested Repository Direction

```text
job-search-assistant/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── db/
│   │   ├── providers/
│   │   └── core/
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   └── package.json
│
├── src-tauri/
│
├── legacy/
│   └── google_sheet/
│
├── docs/
│
├── README.md
└── .gitignore
```

This is a starting point, not a mandatory final structure.

---

# 23. Relationship to Career Goals

Existing resume evidence already includes:

- production ETL
- AWS
- decision systems
- FastAPI
- React
- RAG
- vector databases
- applied ML

This sprint should add evidence for:

- product ownership
- backend architecture
- refactoring
- API integration
- local-first application design
- desktop packaging
- reliability
- cost-aware external API orchestration
- shipping an open-source product

The separate RSNA project should focus more heavily on:

- core ML
- deep experimentation
- medical imaging
- explainability
- MLflow/experiment tracking
- model serving
- ML system design

This separation is intentional.

---

# 24. Final Principle

Build something a real person can use.

Understand every important technical decision.

Ship it.

Document what went wrong.

Do not allow a seven-day project to become a seven-week project.

**Functional → usable → presentable → shipped → learned from → move on.**
