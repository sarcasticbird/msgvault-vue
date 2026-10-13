#!/bin/bash
# launchd entrypoint; configuration stays in the deployment's private .env.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
set -a
source "${MSGVAULT_ENV_FILE:-$APP_DIR/.env}"
set +a
: "${MSGVAULT_HOME:?Set MSGVAULT_HOME}"
: "${MSGVAULT_BINARY:?Set MSGVAULT_BINARY}"
: "${MSGVAULT_SERVICE_PLIST:?Set MSGVAULT_SERVICE_PLIST}"
operation="${1:?Expected import, reconcile, or purge-trash}"
shift
arguments=("$operation" --home "$MSGVAULT_HOME" --binary "$MSGVAULT_BINARY"
  --service-plist "$MSGVAULT_SERVICE_PLIST")
case "$operation" in
  import)
    : "${MSGVAULT_IDENTIFIER:?Set MSGVAULT_IDENTIFIER}"
    arguments+=(--mail-dir "${MSGVAULT_MAIL_DIR:-$HOME/mnt/mail}" --identifier "$MSGVAULT_IDENTIFIER")
    ;;
  reconcile) arguments+=(--mail-dir "${MSGVAULT_MAIL_DIR:-$HOME/mnt/mail}") ;;
  purge-trash) ;;
  *) exit 2 ;;
esac
exec /usr/bin/python3 "$APP_DIR/ops/mail_maintenance.py" "${arguments[@]}" "$@"
