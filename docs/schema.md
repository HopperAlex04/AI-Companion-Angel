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

## Important notes / conventions
- Always use parameterized queries
- Soft deletes use `deleted_at` column
- Timestamps are always left default
- Prefer snake_case
