# Apple Mail jobs for msgvault v0.21

These deployment assets preserve the existing mirror policy. Reconciliation marks
active EMLX messages absent from the mirror, plus trash/spam messages, as deleted
from their source. Purging permanently removes only trash/spam rows and their
foreign-key children. It clears replies to purged parents and removes their
full-text index entries, matching native GC. It does not purge other missing
messages or attachment files.

`run-mail.sh import` performs the existing rsync, imports through the daemon, then
reconciles. Import and purge share `mail-pipeline.lock`. A missing, empty, unreadable,
or truncated Mail tree aborts reconciliation. Cleanup defaults to a read-only plan.

When changes are needed, cleanup unloads its explicitly configured launchd service,
acquires msgvault's `daemon.lock` and `db.write.lock`, applies one SQLite transaction,
and increments `derived_data_revision`. It restores launchd even on failure, then
asks the daemon to rebuild analytics. The plist must specify the same archive with
`--home`. Offline cleanup also acquires both locks and refuses a running daemon.

The managed backend configuration must include:

```toml
[server]
bind_addr = "127.0.0.1"
api_port = 8080
# Set a random api_key privately in this file.
daemon_auto_restart = "never"
daemon_auto_start = false
daemon_idle_timeout = "0s"
```

Store the deployment's private configuration in `.env`, mode 0600:

```sh
MSGVAULT_HOME=/absolute/archive/home
MSGVAULT_BINARY=/absolute/releases/v0.21.0/msgvault
MSGVAULT_SERVICE_PLIST=/absolute/plists/com.msgvault.serve.plist
MSGVAULT_MAIL_DIR=/Users/cdolan/mnt/mail
MSGVAULT_IDENTIFIER=your-account
MSGVAULT_API_URL=http://127.0.0.1:8080
# MSGVAULT_API_KEY must match server.api_key, supplied privately.
MSGVAULT_FRONTEND_HOST=127.0.0.1
```

Run commands from this project's Flox environment:

```sh
flox activate -c 'python3 -m unittest discover -s ops/tests -v'
flox activate -c 'bash ops/run-mail.sh reconcile'
flox activate -c 'bash ops/run-mail.sh reconcile --apply'
flox activate -c 'bash ops/run-mail.sh purge-trash --apply'
```

`prepare_launchd.py` writes candidate definitions only. It preserves the 15-minute
import and 30-minute purge intervals. It invokes the official backend binary
directly and runs the frontend/jobs through this project's Node Flox environment.
It does not use the old backend Flox activation hook that runs `go get`.

```sh
flox activate -c 'python3 ops/prepare_launchd.py \
  --app-dir /absolute/deployment \
  --archive /absolute/archive/home \
  --binary /absolute/releases/v0.21.0/msgvault \
  --output /absolute/plists'
```

Before a live switch, pause the scheduled writers, take a fresh consistent backup,
preserve attachments/configuration and all four old launchd definitions, and retain
the old frontend/binary/scripts. Migration happens when v0.21 opens the archive.
Rollback requires the matching pre-migration archive and old application files.
Do not run the old binary against the migrated database. Rehearse with a separate
archive, launchd prefix, API port, and frontend port before installing live plists.

The frontend proxy authenticates to the archive for anyone who can reach it. Keep
it on loopback or a private tailnet address. A public tunnel requires separate
frontend access control; the archive API key alone does not protect the frontend.
