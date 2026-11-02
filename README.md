# BrightMind Backend

Voice-first AI tutor backend for children. Python + FastAPI + PostgreSQL, built around the
architecture plan: child safety first, regional data residency, a swappable
STT → Claude tutor → moderation → TTS pipeline, and cost discipline.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # leave ANTHROPIC_API_KEY blank to use the offline dev tutor
uvicorn app.main:app --reload   # uses SQLite by default; open http://localhost:8000/docs
pytest -q
```

With Postgres + Redis: `docker compose up --build`.

## Try it

```bash
# 1. Parent registers (consent is mandatory and logged)
curl -X POST localhost:8000/auth/register -H 'content-type: application/json' -d '{
  "email":"mum@example.com","password":"a-long-password","region":"africa",
  "consent_given":true,"consent_policy_version":"2026-01"}'
# 2. Add a child, issue a device token, start a session, send a turn (see /docs)
```

## Layout

```
app/
  config.py          settings (REGION, DB, JWT, Claude model)
  models.py          families, children, consent_records (append-only), sessions, turns, independence_events
  security.py        scrypt password hashing, JWT
  deps.py            auth principals; revoked consent disables all tokens
  routers/           auth, children, sessions (voice turns), dashboard (parent summary)
  services/
    stt.py tts.py    swappable vendor stages (dev stubs included)
    tutor.py         Claude "guided thinking" tutor + 3-level hint system
    moderation.py    independent output filter (rules + optional LLM), fails closed
    pipeline.py      orchestrates the four stages, returns a per-stage audit log
    storage.py       object storage abstraction (local dir now, S3/R2 later)
tests/               API flow, pipeline safety, moderation rules
```

## How it maps to the plan

| Requirement | Where |
|---|---|
| Parent is root of trust; child never authenticates | `routers/auth.py`, `children.py` (device tokens) |
| Consent logging, COPPA/POPIA/GDPR-K audit trail | `ConsentRecord` + event hooks blocking update/delete |
| Revocation | `POST /auth/consent/revoke` locks out parent + child tokens immediately |
| Regional residency | `REGION` env var; registration for another region returns 409. One deployment + DB + bucket per region |
| Moderation independent of tutor | `services/moderation.py`, runs on every reply |
| Audit paper trail | `turns.stage_log` stores per-stage timing/verdicts |
| Independence score | `independence_events` + `/dashboard/children/{id}/summary` |

## Not done yet (honest TODO list)

- **Real STT/TTS vendors.** Dev stubs only. Verify zu/xh/af/st/sw coverage per vendor first.
- **S3/R2 storage** for production buckets.
- **Alembic migrations** (tables currently auto-created; set `AUTO_CREATE_TABLES=false` in prod).
- **DB-level immutability** for `consent_records` (REVOKE UPDATE/DELETE or a trigger); the ORM hook alone is not enough.
- **Verified parental consent** (COPPA requires a verifiable method: card check, ID, signed form), plus email verification and password reset.
- **Rate limiting** (Redis is provisioned but not used yet) and Celery jobs for weekly summaries and data deletion after revocation.
- **Localised safe fallbacks** written by native speakers; the current one is English only.
- **Red-team moderation test suite**; the rule list here is a starting point, not a guarantee.
- **Legal review** of data retention, transcript storage, and consent wording before real children use this.
