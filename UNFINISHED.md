# MediKiosk — Unfinished / Follow-up Tracker
_Last updated: 2026-10-10 (after push `555bbb6`, branch `main` in sync with `origin/main`, tree clean)_

## Health (verified this run)
- [x] `manage.py check` — 0 issues
- [x] `makemigrations --check --dry-run` — No changes detected (fixed: added `medicines/migrations/0001_initial.py`)
- [x] `requirements.txt` — converted from UTF-16+BOM to UTF-8, committed + pushed
- [x] Missing `__init__.py` packages added: `terminology/`, `terminology/services/`, `kiosk/services/`, `kiosk/utils/ocr/preprocessing/`
- [x] Git pushed: `95a837e..555bbb6 main -> main`, ahead/behind = 0/0, `git status` clean

## ❌ Unfinished — failing tests (53 tests, 5 failures + 2 errors)
Run: `venv\Scripts\python.exe manage.py test`
- [ ] `kiosk.tests.KioskAPITests.test_abandoned_session_returns_400` — FAIL (expected 400, got 200)
- [ ] `kiosk.tests.KioskAPITests.test_anonymous_summary_access_rejected` — FAIL
- [ ] `kiosk.tests.KioskAPITests.test_completed_session_returns_400` — FAIL (expected 400, got 200)
- [ ] `kiosk.tests.KioskAPITests.test_nonexistent_session_returns_404` — FAIL (expected 404, got 200)
- [ ] `kiosk.tests.KioskAPITests.test_openrouter_missing_key_raises_configuration_error` — FAIL (`ImproperlyConfigured` not raised)
- [ ] `kiosk.tests.KioskAPITests.test_google_credentials_missing_raises_configuration_error` — ERROR
- [ ] `sensors.tests.SensorsAPITests.test_post_vitals_abnormal` — ERROR
> Likely causes: views returning 200 instead of 4xx for bad/completed sessions, missing auth enforcement on summary endpoint, config-error paths silently falling back instead of raising. Needs triage in `kiosk/views.py`, `kiosk/utils/llm.py`, `sensors/views.py`.

## 🟡 Unfinished — subfolder / repo hygiene notes
- [ ] `.env` and `.env.example` are both **0 bytes** — populate `.env.example` with required keys (`DJANGO_SECRET_KEY`, `DEBUG`, `GEMINI_API_KEY_*`, `SARVAM_API_KEY`, `OPENROUTER_API_KEY`, DB settings, `IP_WEBCAM_URL`)
- [ ] `db.sqlite3` (131 KB) is correctly git-ignored but present locally — decide: keep local dev DB or reset/migrate fresh
- [ ] `media/documents`, `media/cropped` correctly ignored — contain untracked uploads, nothing to commit
- [ ] `venv/` correctly ignored
- [ ] `terminology/services/` has no `tests.py` — add coverage for ICD-11/SNOMED/LOINC services
- [ ] `kiosk/utils/abdm.py` is a **mock** (`push_to_abdm`, `generate_mock_abha_id`) — real ABDM HIE integration pending
- [ ] `download_qwen.py` uses `print()` CLI script — fine as utility, but confirm Qwen model weights are intentionally NOT committed (large files)
- [ ] `body_pointing.py` is a standalone OpenCV demo script at repo root (prints, `show_window=True`) — decide whether to keep at root or move into `kiosk/utils/`
- [ ] No `TODO/FIXME/NotImplemented` markers found in code (only benign `placeholder` variable names in `static/js/app.js` OCR UI + `body_pointing.py` comment)
- [ ] `staticfiles/` build output dir referenced in settings but absent — generated on `collectstatic`, nothing to do for dev

## Subfolder inventory (all tracked, nothing left uncommitted)
| Folder | Contents | Status |
|---|---|---|
| `doctor/` | models/views/urls/serializers/tests + dashboard template + 1 migration | tracked, committed |
| `kiosk/` | models/views/urls/services/utils(ocr/stt/tts)/tests + 3 migrations | tracked, committed |
| `medicines/` | model/view/seed command + **new** `0001_initial` migration | fixed + pushed |
| `medikiosk/` | settings/urls/wsgi/asgi | tracked, committed |
| `sensors/` | vitals API + 2 migrations | tracked, committed |
| `terminology/` | models/views/services(icd11/snomed/loinc) + 1 migration | fixed + pushed |
| `static/`, `templates/` | CSS/JS SPA + kiosk index | tracked, committed |
| `media/` | uploads (ignored) | intentionally untracked |
