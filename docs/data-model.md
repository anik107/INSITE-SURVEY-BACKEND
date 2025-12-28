# InSite Survey MongoDB Design

The schema below satisfies the Functional Requirements Document (FRD) for the InSite Survey Portal. Each collection is stored in the `insite_survey` database (configurable via `MONGODB_DB`).

## Collections

### 1. `users`
Holds Super Admin and Attraction Admin accounts.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `role` | `super_admin` \| `attraction_admin` | Drives permissions |
| `status` | `active` \| `suspended` | Enforces BR-ADM-001 |
| `name`, `email`, `username` | string | `email` + `username` are unique |
| `password_hash` | string | Store hashed password only |
| `attraction_id` | ObjectId | Links admins to an attraction |
| `subscription_status`, `subscription_end` | enum/date | Mirrors dashboard blocking rules |
| `last_login_at`, `created_at`, `updated_at` | datetime | Audit info |

**Indexes**: unique on `username`, unique on `email`, compound on `{role, status}` for quick filters.

### 2. `attractions`
One record per managed attraction.

Fields: `name`, `admin_id`, `monthly_fee`, `yearly_fee`, `subscription_status`, `subscription_plan`, `subscription_start`, `subscription_end`, `auto_renew`, `last_payment_date`, `card_last4`, `card_brand`, timestamps. Unique index on `admin_id` ensures 1:1 mapping.

### 3. `templates`
Embedded structure for template sections and questions.

Fields:
- `title`, `status`, `published_at`, `created_by`.
- `sections[]`: `_id`, `title`, `weight` (1-10 enforced), `allow_notes`, `questions[]`.
- `questions[]`: `_id`, `text`, `type`, `tag`, `allow_na`, `config` (see below).

`config` handles question type specifics:
- `yes_no`: `{ yes_weight, no_weight }`
- `numeric`: `{ min_value, max_value, step }`
- `dropdown`: `{ options[] { value, label, weight } }`

**Business rules**: BR-TPL-001 (single published template) enforced via a unique partial index on `{status: 'published'}`.

### 4. `surveys`
Per-attraction deployments of the published template.

Fields: `template_id`, `attraction_id`, `name`, `status`, `sections[]` (selected subset), `share_id` (unique slug), `qr_code_url`, `published_at`, `archived_at`.

**Indexes**: unique on `share_id`, unique partial index on `{attraction_id, status}` for published surveys (BR-SRV-001).

### 5. `survey_responses`
Immutable documents capturing visitor input.

Fields:
- `survey_id`, `attraction_id`, `template_id`, `submitted_at`.
- `sections[]`: `{ section_id, note, questions[] }`.
- `questions[]`: `{ question_id, type, tag, value, score }`.
- `tag_scores` (aggregated dictionary), `section_scores`, `weather_snapshot`, `duplicate_fingerprint`.

Index on `{survey_id, submitted_at}` plus TTL or dedupe index on `duplicate_fingerprint` (12-hour window) if desired.

### 6. `section_requests`
Requests from Attraction Admins for template updates.

Fields: `attraction_id`, `admin_id`, `section_name`, `description`, `status`, `reviewed_by`, `reviewed_at`, timestamps. Index on `status` supports reviewing backlog.

### 7. `subscription_transactions`
Immutable ledger for every subscription purchase or extension.

Fields: `attraction_id`, `admin_id`, `transaction_type`, `amount`, `status`, `payment_date`, `period_start`, `period_end`, `card_last4`, `card_brand`, `auto_renew_snapshot`, `reference`, timestamps. Index on `{attraction_id, payment_date}` plus `reference` unique index for reconciliation.

### Optional Collections
- `sessions`: if server-side sessions are implemented (FR-AUTH-002).
- `analytics_snapshots`: for pre-aggregated dashboard metrics when performance requires.

## Relationships

- `users.attraction_id` → `attractions._id`
- `surveys.template_id` → `templates._id`
- `surveys.attraction_id` → `attractions._id`
- `survey_responses.survey_id` → `surveys._id`
- `section_requests.attraction_id` → `attractions._id`
- `subscription_transactions.attraction_id` → `attractions._id`

These relations mirror the FRD modules and provide the necessary hooks for analytics, permissions, and subscription enforcement.

## Validation Hints

- Use FastAPI dependencies to enforce the "single published" constraints before inserts/updates.
- Centralize tag values and question types through enums found in `app/models/domain.py`.
- For auditability, update `created_at`/`updated_at` timestamps in repository helpers before persisting documents.
