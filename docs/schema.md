# Database Schema

## Tables

### conversations
- id: integer (PK)
- title: text (not null)
- created_at: datetime (defaults to current timestamp)

### messages
- id: integer (PK)
- conversation_id: integer (FK → users.id)
- role: text (not null)
- content: text (not null)
- metadata: text (nullable JSON)
  - assistant tool-call turns: `{"tool_calls": [...]}`
  - tool results: `{"tool_call_id": "...", "name": "web_search"}`

## Important notes / conventions
- Always use parameterized queries
- Soft deletes use `deleted_at` column
- Timestamps are always left default
- Prefer snake_case
