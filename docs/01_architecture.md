# Architecture Overview

## Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 + SQLite
- **Frontend**: React + TypeScript (served by Tauri)
- **Desktop Shell**: Tauri 2 (manages FastAPI sidecar lifecycle)
- **External APIs**: Bright Data (LinkedIn enrichment), LiteLLM (LLM provider abstraction)
- **Secrets**: OS Keyring via Python `keyring` library

## System Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                     TAURI DESKTOP APP                    │
│  ┌──────────────┐         ┌─────────────────────────┐   │
│  │  React UI    │  HTTP   │   FastAPI Backend       │   │
│  │  (port 1420) │◄───────►│   (port 8080, localhost)│   │
│  └──────────────┘         │                         │   │
│                           │  ┌─────────────────┐    │   │
│                           │  │   SQLite DB     │    │   │
│                           │  │  (local file)   │    │   │
│                           │  └─────────────────┘    │   │
│                           │                         │   │
│                           │  ┌─────────────────┐    │   │
│                           │  │  External APIs  │    │   │
│                           │  │  • Bright Data  │    │   │
│                           │  │  • LiteLLM      │    │   │
│                           │  └─────────────────┘    │   │
│                           └─────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Core Principles
1. **Local-first**: All user data lives in a local SQLite file. No cloud backend.
2. **Cost-aware**: Phase 2 enforces enrichment budgets before calling Bright Data.
3. **Provider-agnostic**: LLM calls route through LiteLLM; user configures provider/model.
4. **Fail gracefully**: Every external call has timeout, retry, and user-facing error mapping.
5. **No hardcoded secrets**: API keys stored in OS Keyring, not in code or SQLite plaintext.
