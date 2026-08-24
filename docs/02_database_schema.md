# Database Schema (SQLite)

All tables use `INTEGER PRIMARY KEY AUTOINCREMENT` unless noted. Foreign keys are logical (enforced in application code) for flexibility.

---

## 1. `user_profile`
Single active profile for the current user.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `profile_id` | `INTEGER` | `PRIMARY KEY` | Always `1` (singleton). |
| `markdown_blob` | `TEXT` | `NOT NULL` | Full resume + profile in Markdown. |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Auto-updated on write. |

---

## 2. `provider_config`
Stores provider metadata. **Secrets (API keys) live in OS Keyring**, not here.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `config_id` | `INTEGER` | `PRIMARY KEY` | |
| `provider_name` | `TEXT` | `NOT NULL` | e.g., `brightdata`, `gemini`, `openai`, `claude` |
| `display_name` | `TEXT` | | Human-readable label. |
| `config_json` | `TEXT` | `NOT NULL` | Non-secret config: `{ "model": "...", "base_url": "...", "dataset_id": "..." }` |
| `is_active` | `BOOLEAN` | `DEFAULT 1` | Only one active per provider. |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | |

**Keyring key format**: `jobsearch:{provider_name}:{config_id}`

---

## 3. `people`
Enriched LinkedIn profiles. **Deduplicated by `linkedin_url`**.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `linkedin_url` | `TEXT` | `PRIMARY KEY` | Canonical URL, lowercase. |
| `public_id` | `TEXT` | `UNIQUE` | LinkedIn public ID (e.g., `gautamwarvatkar`). |
| `name` | `TEXT` | | Full name from Bright Data. |
| `headline` | `TEXT` | | Current role / headline. |
| `company` | `TEXT` | | Current company. |
| `location` | `TEXT` | | City/Country. |
| `about` | `TEXT` | | About section. |
| `experience_json` | `TEXT` | | JSON array of past roles. |
| `education_json` | `TEXT` | | JSON array of education. |
| `certifications_json` | `TEXT` | | JSON array. |
| `activity_json` | `TEXT` | | JSON array of recent posts. |
| `raw_profile_json` | `TEXT` | | Full Bright Data response (for re-parsing). |
| `enriched_at` | `TIMESTAMP` | | When enrichment completed. |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | |

---

## 4. `connections`
Raw imported LinkedIn connections (from CSV). Links to `people` when enriched.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `connection_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | |
| `linkedin_url` | `TEXT` | `NOT NULL` | From CSV. |
| `public_id` | `TEXT` | | Extracted from URL. |
| `first_name` | `TEXT` | | |
| `last_name` | `TEXT` | | |
| `company` | `TEXT` | | Current company (from CSV). |
| `position` | `TEXT` | | Current position (from CSV). |
| `email` | `TEXT` | | If present in export. |
| `is_enriched` | `BOOLEAN` | `DEFAULT 0` | Set true when `people` row exists. |
| `imported_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | |

**Index**: `CREATE INDEX idx_connections_linkedin_url ON connections(linkedin_url);`

---

## 5. `outreach_messages`
Generated + edited messages per person.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `message_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | |
| `linkedin_url` | `TEXT` | `NOT NULL` | FK → `people.linkedin_url`. |
| `generated_text` | `TEXT` | `NOT NULL` | Raw LLM output. |
| `final_text` | `TEXT` | | User-edited version (NULL = never edited). |
| `user_context` | `TEXT` | | Extra note from user for this outreach. |
| `generated_at` | `TIMESTAMP` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | |
| `finalized_at` | `TIMESTAMP` | | Set when user clicks Save/Copy. |

---

## 6. `enrichment_logs`
Audit trail of every Bright Data enrichment attempt.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `log_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | |
| `linkedin_url` | `TEXT` | `NOT NULL` | |
| `snapshot_id` | `TEXT` | | Bright Data snapshot ID. |
| `status` | `TEXT` | `NOT NULL` | `pending`, `success`, `failed`. |
| `error_message` | `TEXT` | | If failed. |
| `started_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | |
| `completed_at` | `TIMESTAMP` | | |
