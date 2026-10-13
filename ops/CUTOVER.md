# rack-mini v0.21.0 cutover

Prepared on 2026-10-12. This runbook changes running services. The isolated trial
and candidate files can be inspected before running it.

Prepared paths on rack-mini:

- Official binary: `/Users/cdolan/Projects/MessageVault/releases/v0.21.0/msgvault`
- Frontend/jobs: `/Users/cdolan/Projects/MessageVault/releases/v0.21.0/frontend`
- Config/plists: `/Users/cdolan/Projects/MessageVault/upgrade-trial-20261012-v0.21.0/candidate/live`
- Live archive: `/Users/cdolan/.msgvault`
- Existing binary/frontend/scripts remain at their original paths.

The candidate binds the archive API to `127.0.0.1:8080`, enables a private random
API key, and binds the frontend to tailnet address `100.107.58.124:3000`. The key
is stored in the private backend config and frontend `.env`. The 900-second import
and 1,800-second purge intervals stay the same. MCP and public tunneling are
separate work and are not enabled by this cutover.

## Before switching

1. Verify the mini still owns the configured tailnet address. Validate the four
   candidate plists with `plutil -lint`. Run `npm ci`, tests, build, lint, audit,
   and the Python tests inside the release frontend's Flox environment.
2. Wait for any existing import/purge to finish. Unload those two live launchd
   jobs, then the frontend and backend. Confirm the processes have exited before
   copying the archive. Do not merely send a signal to a KeepAlive process.
3. Create a new mode-0700 backup directory. APFS-clone the entire stopped
   `.msgvault` directory, including any WAL/SHM files, attachments, config, and
   tokens. Copy all four original launchd plists there. Record the old binary's
   checksum and existing paths. This backup must be fresh; the October 12 trial
   baseline is not the cutover backup.
4. Save the backup directory in the cutover log. Keep the writers unloaded until
   acceptance passes or rollback finishes.

## Switch and accept

1. Install the private candidate config as `~/.msgvault/config.toml`, mode 0600.
   Install the four candidate plists in `~/Library/LaunchAgents/`.
2. Bootstrap `com.msgvault.serve` in `gui/501`. Its first open migrates the live
   archive. Wait for `/health` and authenticated `/api/v1/stats/total` to respond.
3. Bootstrap `com.msgvault.vue-dev`. Check
   `http://100.107.58.124:3000/api/v1/stats/total` through the frontend without a
   browser API key. Direct archive API access without the key must return 401.
4. Verify message counts against the fresh backup, inspect an existing message,
   and compare an original attachment download's SHA-256. Native Parquet
   analytics omits rows without `sent_at`; compare matching visibility rules.
5. Run `bash ops/run-mail.sh reconcile` inside the release frontend's Flox
   environment. Review the read-only plan before the first apply.
6. Run one import/reconciliation cycle. Verify its import error count, exact
   cleanup candidates, daemon health, and refreshed API counts. Keep output in
   private logs. Repeated reconciliation must make no further changes.
7. Bootstrap the import and purge schedules only after acceptance. Record the
   four loaded definitions and the new binary version.
8. Check `~/.local/bin/msgvault` separately from the service binary. Preserve any
   old executable in the fresh backup, then point this CLI at the official
   release and verify `version` and `stats`. The mini had a separate v0.13 CLI.

The candidate's `MSGVAULT_SERVICE_PLIST` points to the preserved candidate plist
path, which must remain available for maintenance to bootstrap the daemon.

## Rollback

1. Unload all four new launchd jobs and wait for their processes to exit. Preserve
   the failed upgraded archive separately for investigation. Never run the old
   binary against the migrated database.
2. Move the upgraded `.msgvault` directory aside and APFS-clone the complete fresh
   pre-cutover archive back to `.msgvault`. Restore all four saved launchd plists.
   The old binary, frontend, scripts, and Flox environments remain at their
   original paths.
   Restore the saved `msgvault-cli-old` executable to `~/.local/bin/msgvault`,
   replacing the release symlink, so CLI and daemon versions match again.
3. Bootstrap the old backend and frontend. Verify health, counts, message detail,
   and an attachment before restoring the old import/purge schedules.
4. Record that rollback returns the archive to the backup's timestamp. Keep the
   upgraded archive so any later ingested mail can be recovered or reimported.

The rollback rehearsal used the preserved old binary with a separate clone of
its matching pre-migration archive. It verified 84,506 messages, 16,844 attachment
records, and a working API. It did not restore anything over the live archive.
