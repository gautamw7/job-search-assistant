# Phase 2: My Network / High-Impact Connections

## Goal
Enable a user to:
1. Import a LinkedIn connections CSV (or JSON).
2. Apply cheap, local filters to reduce the set (e.g., by company, title, keywords).
3. Select an enrichment budget (max number of profiles to call Bright Data on).
4. Enrich the top N candidates (after filtering and ranking).
5. Rank the enriched candidates (simple scoring: title relevance, company match, seniority, etc.).
6. Present a ranked list (e.g., top 75) for the user to review.
7. Let the user select a person, then reuse Phase 1 flow to generate an outreach message.

## Workflow (Step-by-Step)

```text
[CSV Upload]
          ↓
    Parse & Validate → insert into `connections` table
          ↓
    Local Filtering (rules-based, no API):
       - Remove current coworkers? (optional)
       - Keep only titles containing keywords (Data Scientist, Engineer, etc.)
       - Keep only companies in target list
       - Keep only locations in target list
          ↓
    → Filtered Connections (still in `connections` table)
          ↓
    Ranking Score (cheap, deterministic):
       - Title match score (0-2)
       - Company match score (0-2)
       - Seniority inferred from title (e.g., "Director" > "Manager")
       - Keyword match in company/title
          ↓
    → Sorted by score DESC
          ↓
    Take Top K where K = enrichment_budget (user-configured, default 100)
          ↓
    For each in Top K:
       - If not already enriched (`is_enriched = false`), call Bright Data
       - On success: insert/update `people` row, set `connections.is_enriched = true`
          ↓
    Re-score enriched candidates? (optional: re-run ranking with enriched data)
          ↓
    Present Ranked List (UI): show name, company, title, match score, enrichment status
          ↓
    User selects a row → navigate to Phase 1 outreach flow with that LinkedIn URL
          ↓
    (Re-use Phase 1 endpoints: /api/v1/enrich, etc.)
```

## API Contracts (Backend Endpoints)

### `POST /api/v2/connections/import`
- **Description**: Upload and parse a LinkedIn connections CSV.
- **Body**: multipart/form-data with file field `connections_csv`.
- **CSV Columns expected** (at minimum): `First Name`, `Last Name`, `Company`, `Position`, `Linkedin_Link`, `Connected` (optional).
- **Response**:
  ```json
  {
    "imported_count": 1234,
    "skipped_duplicates": 12,
    "errors": [ ... ]
  }
  ```
- **Logic**: For each row, extract `linkedin_url`. Insert into `connections` table if not exists (by `linkedin_url`). Update fields if exists? (Product decision: treat import as additive; do not overwrite existing notes.)

### `GET /api/v2/connections/filtered`
- **Description**: Get filtered & ranked connections (for UI pagination).
- **Query Params**:
  - `budget`: integer (enrichment budget, e.g., 100)
  - `offset`: integer (for pagination)
  - `limit`: integer (page size, e.g., 50)
- **Response**:
  ```json
  {
    "total": 567,
    "filtered_count": 89,
    "connections": [
      {
        "connection_id": ...,
        "linkedin_url": "...",
        "first_name": "...",
        "last_name": "...",
        "company": "...",
        "position": "...",
        "is_enriched": true/false,
        "score": 0.85,
        "person": { ... } // if enriched, otherwise null
      }
    ]
  }
  ```
- **Logic**:
  1. Start with all rows in `connections`.
  2. Apply local filters (from user settings or defaults).
  3. Compute a deterministic score per row (no API calls).
  4. Sort by score DESC.
  5. Return the slice `[offset: offset+limit]`.
  6. Also return `total` (after filters) and `filtered_count`.

### `POST /api/v2/connections/enrich-batch`
- **Description**: Enrich the next batch of connections up to the budget.
- **Body**: `{ "budget": 100 }` (or reuse last used budget from settings).
- **Response**:
  ```json
  {
    "processed": 20,
    "enriched": 18,
    "failed": 2,
    "errors": [ ... ]
  }
  ```
- **Logic**:
  1. Select from `connections` where `is_enriched = false`, ordered by the same ranking score used in `/filtered`, limit = budget.
  2. For each, call Bright Data enrichment (same as Phase 1).
  3. On success: upsert into `people`, set `connections.is_enriched = true`, log to `enrichment_logs`.
  4. On failure: log error, leave `is_enriched = false` (so retry can happen later).

## Local Filtering Rules (Examples)
- **Title**: Must contain (case-insensitive) any of: `data`, `scientist`, `engineer`, `analyst`, `research`, `ml`, `ai`.
- **Company**: Not in a deny-list (current employer, staffing agencies).
- **Location**: Preferred countries/cities (from user settings).
- **Connected**: Only rows where `Connected` column equals `"Connected"` (if present).

## Ranking Score (Simple, Deterministic)
Score =
  +2.0 if title contains target role keywords (e.g., "Data Scientist")
  +1.5 if title contains related keywords (e.g., "Engineer", "Analyst")
  +1.0 if company matches target company list
  +0.5 if location matches preferred location
  +0.1 per year of inferred seniority (from title: "Director"=2, "Manager"=1, etc.)
Normalize to 0-1 range.

## Notes
- The same `/api/v1/enrich` endpoint from Phase 1 can be called manually for any connection after reviewing the ranked list.
- Enrichment logs (`enrichment_logs`) capture every Bright Data attempt for debugging and cost tracking.
- The `connections` table acts as the source of truth for what the user imported; the `people` table holds enriched subsets.
