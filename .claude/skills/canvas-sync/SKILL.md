---
name: canvas-sync
description: Sync Canvas coursework (grades, deadlines, files) and push it to your Silla dashboard. Use when the user asks to sync/update/refresh their Canvas data, or on a schedule.
---

# canvas-sync

Refreshes your "Silla" dashboard (a published Claude Artifact) with the latest data from
Canvas. Two stages, because only a Claude Code turn can write to the Artifact's database —
a plain script cannot call it directly.

Note: this Artifact flow is an **optional bonus** — `./scripts/run_sync.sh` alone already
regenerates a fully working local `dashboard.html` with zero Claude/subscription
involvement (see the README). Only use this skill if the user specifically wants the
hosted, live-updating Artifact version in addition to that.

**Dashboard URL**: read `DASHBOARD_URL` from the project's `.env` file
(`~/PycharmProjects/canvas-dashboard/.env`, or wherever you cloned this project). If it's
empty, you haven't published your own dashboard yet — see the project README's setup steps
first (publish `artifact/dashboard.html`, then save the resulting URL into `.env` as
`DASHBOARD_URL=...`), then come back to this skill.

## Steps

1. Run the local sync script, which authenticates to Canvas, fetches grades/assignments/
   calendar events, and downloads new/changed files into `<COURSE_FILES_ROOT>/<course>/_synced/`
   (`COURSE_FILES_ROOT` defaults to `~/Documents/canvas files`, overridable in `.env`), and
   writes `artifact_payload/latest.json`:

   ```bash
   cd ~/PycharmProjects/canvas-dashboard && ./scripts/run_sync.sh
   ```

   This is idempotent — safe to run any number of times. If it reports errors (printed at
   the end, non-zero exit), still proceed to step 2 with whatever `latest.json` it wrote —
   a partial sync is better than a stale dashboard. Only stop and report to the user if the
   script fails before writing `latest.json` at all (e.g. auth failure — check the Canvas
   token and `CANVAS_BASE_URL` in `.env`).

2. Read `artifact_payload/latest.json`. It has this shape:
   ```
   { "courses": [...], "calendar_events": [...], "files": [...], "sync_meta": {...} }
   ```

3. Reshape it into the Artifact DB's collections and push with ONE `write_db` batch call
   (db_op: "batch") against the `DASHBOARD_URL` read in step 0:

   - `courses/<canvas_course_id>` (one doc per course) ← each entry in `courses`, dropping
     `canvas_course_id`/`local_folder_name` from the body (keep `name`,
     `current_score_pct`, `assignment_group_breakdown`, `last_synced_at`).
   - `sync/calendar` (single doc) ← `{"events": calendar_events}`, sorted by `due_at` with
     nulls last.
   - `files/<course_id>` (one doc per course) ← group the flat `files` array by
     `course_id` into `{"course_name": ..., "files": [{filename, size_bytes, canvas_url}, ...]}`
     — do NOT create one document per file (the db caps at 5000 docs/artifact; aggregating
     per course keeps this small regardless of how many files accumulate). Drop
     `local_path` — it's a path on this machine only, meaningless to the published page.
     `canvas_url` is the file's page on Canvas itself
     (`<CANVAS_BASE_URL>/courses/<course_id>/files/<file_id>`) — the dashboard links to it
     so viewers can open/download the file straight from Canvas. Do NOT try to re-host
     files via the Artifact `assets` capability: it only accepts pdf/image/audio/text
     types, and most course materials are .pptx/.docx, which it rejects outright.
   - `sync/meta` (single doc) ← the `sync_meta` object (`last_sync_at`, `courses_synced`,
     `assignments_synced`, `files_downloaded`, `errors`).

   Use `set` (full replace) for every doc — each push is a complete, fresh snapshot, not an
   incremental merge.

4. Tell the user a one-line summary: courses synced, new files downloaded, and any errors
   from `sync_meta.errors` (translate the gist into plain language, e.g. "не удалось
   скачать 1 файл — таймаут, попробуем на следующей синхронизации").

## Notes

- The Canvas API token lives only in the project's local `.env` — never read it, print it,
  or include it in anything written to the Artifact. Same for the raw `local_path` values —
  they're this machine's filesystem, not useful or safe to publish.
- If the set of course ids changes (a course disappears or a new one appears), just push
  what's current — no need to explicitly delete stale docs unless the user asks for
  cleanup, since a handful of leftover course cards is harmless and the next real semester
  will just add new ones.
- This dashboard and its data are private to you (the Artifact's `db` capability makes it
  organization-internal — see the README's "Sharing" section). Never push another person's
  Canvas data into your own dashboard, and never point this skill at someone else's
  `DASHBOARD_URL`.
