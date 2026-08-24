# Job Search Assistant

A local-first, open-source desktop application to streamline LinkedIn networking and job searching workflows.

## Overview

This application helps users:
1. **Enrich LinkedIn profiles** using Bright Data API
2. **Generate personalized outreach messages** using LLMs (via LiteLLM abstraction)
3. **Import and filter LinkedIn connections** to find high-impact contacts
4. **Persist all data locally** in SQLite for privacy and offline use
5. **Manage API credentials securely** via OS Keyring

## Features

- **Phase 1 (Reach Out)**: Single URL enrichment → LLM message generation → Review/edit/save
- **Phase 2 (My Network)**: CSV import → Local filtering/ranking → Selective enrichment → Outreach
- **Local-first architecture**: All data stored in encrypted SQLite database
- **Secure credential storage**: API keys stored in OS Keyring (Keychain/Credential Manager)
- **Cost-aware**: Configurable enrichment budgets to prevent API overuse
- **Provider-agnostic**: Switch between LLM providers (Gemini, Claude, OpenAI) without code changes
- **Desktop packaging**: Built with Tauri 2 for cross-platform distribution

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 + SQLite
- **Frontend**: React + TypeScript
- **Desktop Shell**: Tauri 2
- **External APIs**: Bright Data (LinkedIn enrichment), LiteLLM (LLM abstraction)
- **Secrets Management**: Python `keyring` library
- **Testing**: Pytest with isolated test database

## Project Structure

```
job-search-assistant/
├── backend/
│   ├── app/                  # FastAPI application
│   │   ├── api/              # API endpoints
│   │   ├── services/         # Business logic services
│   │   ├── db/               # Database models and repositories
│   │   └── providers/        # API provider integrations
│   ├── tests/                # Backend unit tests
│   └── pyproject.toml        # Backend dependencies
├── frontend/                 # React + TypeScript UI
├── src-tauri/                # Tauri 2 desktop shell
├── docs/                     # Documentation
│   ├── 01_architecture.md    # System overview and principles
│   ├── 02_database_schema.md # Complete database schema
│   ├── 03_phase1_reachout.md # Phase 1 workflow details
│   ├── 04_phase2_network.md  # Phase 2 workflow details
│   └── 05_sprint_roadmap.md  # 7-day sprint plan
└── legacy/                   # Original Google Sheet workflow (reference only)
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend development)
- Rust toolchain (for Tauri compilation)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/job-search-assistant.git
   cd job-search-assistant
   ```

2. Install backend dependencies:
   ```bash
   uv sync
   ```

3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. Set up environment variables (copy from `.env.example`):
   ```bash
   cp .env.example .env
   # Edit .env to add your API keys (or let the app prompt for them via OS Keyring)
   ```

### Development

#### Backend Only

Run the FastAPI server:
```bash
uv run job-search-assistant
```

API will be available at `http://localhost:8080`

#### Frontend Only

Start the React dev server:
```bash
cd frontend
npm run dev
```

UI will be available at `http://localhost:5173`

#### Full Desktop App (Tauri)

Build and run the Tauri application:
```bash
# Development mode
cargo tauri dev

# Production build
cargo tauri build
```

## API Endpoints

### Phase 1: Reach Out

- `POST /api/v1/profile` - Set/update user profile/resume
- `POST /api/v1/enrich` - Enrich LinkedIn URL and generate outreach message
- `PUT /api/v1/messages/{id}` - Update final edited message

### Phase 2: My Network

- `POST /api/v2/connections/import` - Import LinkedIn connections CSV
- `GET /api/v2/connections/filtered` - Get filtered & ranked connections
- `POST /api/v2/connections/enrich-batch` - Enrich connections up to budget

## Database Schema

See [docs/02_database_schema.md](docs/02_database_schema.md) for complete table definitions.

## Testing

Run the complete test suite:
```bash
make test
# or
uv run pytest
```

Tests cover:
- Database schema and table creation
- User profile management (resume parsing, storage)
- Connection import and CSV validation
- Provider configuration and Keyring integration
- Schema validation
- Placeholder tests for upcoming features

## Security

- **No hardcoded secrets**: API keys never stored in code or plaintext database
- **OS Keyring integration**: Credentials stored in system-specific secure storage:
  - macOS: Keychain
  - Windows: Credential Locker
  - Linux: Secret Service (Libsecret)
- **Local-first**: All personal data remains on user's device
- **Minimal permissions**: Only requests necessary permissions for LinkedIn enrichment and messaging

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with inspiration from existing LinkedIn networking workflows
- Uses Bright Data for reliable LinkedIn profile enrichment
- Leverages LiteLLM for clean LLM provider abstraction
- Package desktop application with Tauri 2 for excellent user experience
