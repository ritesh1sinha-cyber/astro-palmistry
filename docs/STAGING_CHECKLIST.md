# GrahaRekha — staging checklist

Use this before pointing a staging domain at the app. Local dev commands are in `fixtures/README.txt`.

## Environment (API)

- [ ] `DEV_LOGIN=0` — guest and admin test login disabled
- [ ] `INLINE_WORKER=1` only if you accept single-process job queue (otherwise run a worker)
- [ ] Google OAuth: `GOOGLE_CLIENT_ID` set; site `CONFIG.googleClientId` matches
- [ ] UPI / payment gateway configured; `CONFIG.upiId` or server-generated QR intents work
- [ ] CORS allows the staging site origin
- [ ] Report files directory writable and served at `/reports/`

## Environment (static site)

- [ ] `CONFIG.apiBase` empty for same-origin deploy, or set to staging API URL
- [ ] Remove `?dev=1` from any shared links — admin button must stay hidden
- [ ] Contact email, phone, WhatsApp updated from placeholders

## Smoke tests (manual)

### Auth
- [ ] Google Sign-In completes; `/api/me` returns user
- [ ] Guest login is **not** available when `DEV_LOGIN=0`
- [ ] Sign-out clears session and reading state

### Birth chart
- [ ] Place autocomplete fills lat/lon/tz (or manual coords toggle works)
- [ ] Chart summary (free) returns lagna / Moon / dasha
- [ ] Full report job completes; free iframe loads; paywall shows `paidSections`
- [ ] Admin (staging only, if enabled) sees paid half without payment

### Palm
- [ ] Both hands upload or capture; job queue shows progress / stuck messaging
- [ ] Free reading renders; UPI unlock flow opens QR or mobile intent
- [ ] Payment poll unlocks full report (or mock simulate in dev)

### Horary / match / muhurat / BTR
- [ ] Horary: one answer card + free iframe; paid embed has **no** engine jargon
- [ ] Match, muhurat, BTR jobs complete and render

## Automated (local)

```bash
python e2e_design.py
```

Expect **12/12 PASS** for report HTML design checks. Live job polling (`e2e_check.py`) may hang with `INLINE_WORKER=1` — run with a real worker for full E2E.

## Optional quality

- [ ] `sentence-transformers` installed if Bhardwaj semantic lane is required (see API logs on first full report)
- [ ] Real palm photos (not synthetic fixtures) for MediaPipe validation
- [ ] OAuth + real UPI payment tested once on staging hardware

## Do not ship to production with

- Default admin credentials (`admin@graharekha.test` / `graha-admin`)
- `DEV_LOGIN=1`
- Empty `googleClientId` if you expect real accounts
- Placeholder contact numbers
