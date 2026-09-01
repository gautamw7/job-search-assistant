# Frontend Integration & Architecture Guide

This document provides a comprehensive guide for frontend engineers integrating with the **Job Search Assistant API**. It covers data contracts, endpoint specifications, state management patterns, and core workflows (batch generation, history logging, and multi-turn regeneration).

---

## 1. Base URL & Conventions

* **Base URL:** `http://localhost:8000`
* **Content-Type:** `application/json` (except file uploads which use `multipart/form-data`)
* **CORS:** Enabled for all origins (`*`) in development.

---

## 2. API Endpoints Reference

### A. Resume Management (`/resume`)

* **`GET /resume/`**
  * **Description:** Retrieves the parsed resume in Markdown format.
  * **Response:** Plain text (Markdown string) or `404` if no resume has been uploaded yet.

* **`POST /resume/`**
  * **Description:** Uploads a PDF resume, parses it using PyMuPDF4LLM, and caches it as Markdown.
  * **Request Body:** `multipart/form-data` with key `file` (PDF format only).
  * **Response:**
    ```json
    {
      "message": "Resume uploaded and converted to Markdown successfully."
    }
    ```

---

### B. User Communication Style (`/user-communication`)

* **`GET /user-communication/`**
  * **Description:** Retrieves the active communication style configuration and text.
  * **Response:**
    ```json
    {
      "style": "- Greeting: Casual\n- Directness: High...",
      "config": { ... }
    }
    ```

* **`GET /user-communication/prompt`**
  * **Description:** Retrieves the meta-prompt and questionnaire used to analyze writing style.
  * **Response:**
    ```json
    {
      "prompt": "...",
      "default": "...",
      "questions": [
        { "id": "greeting", "question": "How do you usually greet?", "options": ["Hey", "Hi"] }
      ]
    }
    ```

* **`POST /user-communication/update`**
  * **Description:** Updates the user's active writing style.
  * **Request Body:**
    ```json
    {
      "style": "Casual and punchy tone."
    }
    ```
  * **Response:**
    ```json
    {
      "message": "User communication style updated successfully."
    }
    ```

---

### C. Message Generation & Batch Pipeline (`/generate`)

#### 1. Batch Generate Messages (`POST /generate/generate_message`)
* **Description:** Accepts a dictionary of target LinkedIn URLs mapped to their specific user notes and preferences, enriches them via BrightData, and generates initial outreach messages using Gemini.
* **Request Body:**
  ```json
  {
    "https://www.linkedin.com/in/recruiter-a": {
      "user_note": "Met at AI hackathon",
      "user_preferences": "Keep it under 80 words, concise."
    },
    "https://www.linkedin.com/in/recruiter-b": {
      "user_note": "Hiring for backend role",
      "user_preferences": "Standard 100-120 words."
    }
  }
  ```
* **Response:**
  ```json
  {
    "https://www.linkedin.com/in/recruiter-a": "Hey [Name], great meeting you at the hackathon...",
    "https://www.linkedin.com/in/recruiter-b": "Hi [Name], saw your team is expanding..."
  }
  ```

#### 2. Get Generation History (`GET /generate`)
* **Description:** Retrieves the entire append-only history log stored in `data/generated_messages.json`.
* **Response Structure (Append-Only History Log):**
  ```json
  {
    "https://www.linkedin.com/in/recruiter-a": [
      {
        "prompt_context": {
          "user_resume": "...",
          "user_communication_style": "...",
          "user_preferences": "...",
          "recipient_enrich_data": "...",
          "user_notes": "...",
          "system_prompt": "...",
          "template": "..."
        },
        "generated_message": "Initial generated message text...",
        "generated_at": "2026-08-29 21:00:00"
      }
    ]
  }
  ```
  * **Frontend Tip:** To display the latest generated message for any URL, always access the last item in the history array: `history[url][history[url].length - 1].generated_message`.

#### 3. Multi-Turn Regeneration (`POST /generate/regenerate_message`)
* **Description:** Reconstructs the exact multi-turn chat context for a specific LinkedIn URL, appends the user's new tweak/note to the final turn, and queries Gemini to overwrite/append a new generation.
* **Query Parameters:**
  * `linkedin_url` (string, required): The target profile URL.
  * `additional_note` (string, optional): New instruction or tweak (e.g. *"Make it more punchy"*).
  * `additional_preferences` (string, optional): Updated word count or style preference.
* **Request Example:**
  ```http
  POST /generate/regenerate_message?linkedin_url=https%3A%2F%2Fwww.linkedin.com%2Fin%2Frecruiter-a&additional_note=Mention%20our%20mutual%20connection
  ```
* **Response:**
  * Returns the newly generated message string (plain text/JSON response depending on FastAPI return type).

---

## 3. Recommended Frontend State Flow

1. **Intake / Batch Queue ($n$ targets):**
   * Provide dynamic rows (`+` / `-`) where users input `LinkedIn URL` and optional `User Notes`.
   * On clicking **"Generate All"**, construct the `targets` JSON object and call `POST /generate/generate_message`.
2. **Multi-Card Dashboard:**
   * Transition to a grid of cards once generation completes.
   * Fetch full history via `GET /generate` to support offline review and browsing past generations.
3. **Personalization / Pop-Out Editor:**
   * Inside each card, allow the user to type feedback/tweaks and click **"Regenerate"**.
   * Call `POST /generate/regenerate_message` with query parameters to update the card content dynamically.
