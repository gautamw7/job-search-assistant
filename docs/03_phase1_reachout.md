# Phase 1: Reach Out

## Goal
Enable a user to:
1. Configure their profile/resume (once).
2. Enter a LinkedIn URL.
3. Optionally add context (free-text note).
4. Trigger enrichment via Bright Data.
5. Generate a personalized outreach message via an LLM.
6. Review/edit the message.
7. Copy or save the message.
8. See the enriched person and message persisted locally.

## Workflow (Step-by-Step)

```text
[User Profile] + [LinkedIn URL] + [User Context]
          ↓
    Validate URL (must be linkedin.com/in/...)
          ↓
    Bright Data Enrichment → Raw Profile JSON
          ↓
    Normalize Profile → structured text (name, headline, company, etc.)
          ↓
    Build LLM Prompt:
       - System: Expert LinkedIn networking assistant
       - Fixed: User's resume (markdown_blob from user_profile)
       - Fixed: User's professional context (from user_profile or separate field?)
       - Variable: Enriched recipient profile (normalized text)
       - Variable: User-provided context for this outreach (free text)
          ↓
    Call LLM (via LiteLLM) → Generate Message
          ↓
    Quality Checks (length, profanity, placeholder detection) → Optional
          ↓
    Present Message to User for Review/Edit
          ↓
    User edits or copies message
          ↓
    Save:
       - Upsert `people` row (by linkedin_url) with enriched data
       - Insert `outreach_messages` row (generated_text, final_text, user_context, timestamps)
```

## API Contracts (Backend Endpoints)

### `POST /api/v1/profile`
- **Description**: Set or update the user's profile/resume.
- **Body**: `{ "markdown_blob": "<markdown string>" }`
- **Response**: `200 OK` with saved profile.

### `POST /api/v1/enrich`
- **Description**: Enrich a LinkedIn URL and generate an outreach message.
- **Body**:
  ```json
  {
    "linkedin_url": "https://linkedin.com/in/...",
    "user_context": "Optional note for this outreach"
  }
  ```
- **Response**:
  ```json
  {
    "person": { ... }, // normalized person object (from people table)
    "message": {
      "generated_text": "...",
      "final_text": null, // until edited
      "user_context": "...",
      "generated_at": "...",
      "finalized_at": null
    }
  }
  ```

### `PUT /api/v1/messages/{message_id}`
- **Description**: Update the final edited text of a message.
- **Body**: `{ "final_text": "<edited message>" }`
- **Response**: `200 OK` with updated message.

## Error Handling
- **Bright Data**: Invalid URL, not found, timeout, rate limit → map to 4xx/5xx with user-friendly message.
- **LLM**: Missing API key, timeout, malformed output → retry with fallback models, then error.
- **Validation**: URL must be a LinkedIn profile URL.

## Notes
- The user's profile (markdown_blob) is stored in `user_profile` (single row).
- The `user_context` in the enrichment request is stored in `outreach_messages.user_context`.
- If the LinkedIn URL already exists in `people`, we skip re-enrichment unless forced? (Product decision: maybe allow refresh?)
