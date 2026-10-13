# rack-mini MCP through Tailscale Funnel

Verified 2026-10-13. The first consumer is Hark at https://hark.com, whose
connection flow accepts HTTPS Streamable HTTP and a bearer token through a
secure credential form. The user confirmed the Hark connection worked on
2026-10-13. ChatGPT OAuth setup is deferred.

Connection:

- URL: `https://rack-mini.tail659d03.ts.net/mcp`
- Transport: Streamable HTTP
- Header: `Authorization: Bearer <dedicated MCP key>`
- Permissions: 36 read-only tools. No HTTP write flags are enabled.

The key is stored privately on rack-mini in
`/Users/cdolan/Projects/MessageVault/mcp-funnel-20261013/.env`, under
`MSGVAULT_MCP_API_KEY`. Enter only the token in Hark's secure form. Do not paste
it into chat. To copy it to the clipboard from blackbook:

```sh
ssh rack-mini 'sed -n "s/^MSGVAULT_MCP_API_KEY=//p" ~/Projects/MessageVault/mcp-funnel-20261013/.env' | pbcopy
```

## Service configuration

Deployment root on rack-mini:
`/Users/cdolan/Projects/MessageVault/mcp-funnel-20261013`

- `com.msgvault.mcp` runs the official v0.21.0 binary on `127.0.0.1:8081`.
  Its private `mcp-config.toml` uses a dedicated incoming `[server].api_key`
  and `[remote]` to contact the existing daemon at `http://127.0.0.1:8080`
  with the daemon's separate private key. It does not use `--local`, which
  would override that explicit remote configuration.
- `com.msgvault.mcp-proxy` runs Caddy 2.11.7 through the deployment root's
  isolated, locked Flox environment. It listens only on `127.0.0.1:8082`.
  Its Caddyfile permits the intended hostname and `/mcp` path, preserves
  incoming bearer authentication, and normalizes the upstream Host header
  to `127.0.0.1:8081`. This preserves msgvault's Host-header protection.
- Tailscale Funnel persists in background mode, forwarding HTTPS port 443
  on `rack-mini.tail659d03.ts.net` to `http://127.0.0.1:8082`.
- Original archive configuration, Vue service, and mail schedules remain
  in place. The public route does not serve the REST API or Vue app.

Both new launchd definitions are installed in `~/Library/LaunchAgents/` and
copied into the deployment root. Logs live in its `logs/` directory. The
credential environment and MCP config are mode 0600.

## Verification

`public-mcp-acceptance.json` and `final-evidence.json` in the deployment root
record successful checks through public DNS and the Funnel relay with TLS
certificate verification enabled:

- Missing and incorrect tokens return 401.
- Authenticated initialization, tool discovery, and `get_stats` succeed.
- All 36 exposed tools have `readOnlyHint=true`.
- Public `/api/v1/stats/total` and `/src/api/client.ts` return 404.
- Caddy rejects an unrecognized Host; the native listener retains its own
  Host-header checks.
- All six msgvault launchd jobs are loaded. Native MCP and proxy listeners
  bind only to loopback; the existing Vue service remains on the tailnet.

No secrets are included in these reports. A local report copy is kept in
`.agents/wip/mcp-funnel-evidence.json`.

The initial Funnel request was rejected by automatic approval review because
the assumed ChatGPT consumer lacked compatible OAuth. After the user clarified
Hark's bearer-token support, a dedicated MCP key was configured and tested, and
the Funnel action passed review. No OAuth provider was installed.

## Disable or remove this connection

First disable the temporary health job using the commands below, then disable
the specific public route on rack-mini:

```sh
/Applications/Tailscale.app/Contents/MacOS/Tailscale funnel --https=443 off
```

Then, if removing the local MCP services too:

```sh
launchctl bootout gui/$(id -u)/com.msgvault.mcp-proxy
launchctl bootout gui/$(id -u)/com.msgvault.mcp
```

Move their two launchd plist files out of `~/Library/LaunchAgents/` to prevent
them returning at login. Preserve the deployment root for inspection. The
original Serve/Funnel configuration was empty and is saved as
`serve-before.json`; do not reset unrelated routes added later.

To rotate the consumer key, replace both `MSGVAULT_MCP_API_KEY` in the private
`.env` and `[server].api_key` in `mcp-config.toml`, then restart only the MCP
service and update Hark's secure credential. Leave `[remote].api_key` unchanged
unless the archive daemon's key is also being rotated. Never share the daemon
key with consumers.

## Recover a stalled Funnel

On 2026-10-13 Hark reported 502 while all local services and tailnet HTTPS
remained healthy. Both public relay addresses closed TLS handshakes. Refreshing
the Funnel route did not help. An approved detached `tailscale down
--accept-risk=lose-ssh` followed by `tailscale up` restored one relay immediately;
the second recovered several minutes later. Authenticated public MCP queries
passed after recovery. The archive, Vue, MCP, and proxy processes stayed running
during the reconnect, and no credential or route destination changed.

This resembles the unresolved upstream Funnel/control-plane issue:
https://github.com/tailscale/tailscale/issues/21114

Use public DNS relay addresses when checking health. Tailnet DNS resolves this
hostname directly to the mini and can hide a public Funnel outage. An
unauthenticated request to `/mcp` should return 401, not fail TLS. Diagnostic
evidence is retained privately under `outage-20261013/` in the deployment root.

`ops/restart_tailscale.py` is also installed as `restart-tailscale.py` in the
deployment root. By default it only checks the current route and both public
relays. With `--apply`, it reconnects the client through `tailscale down
--accept-risk=lose-ssh` and `tailscale up`. Recovery runs even if disconnect
reports an error. Public relays may need several minutes to recover; the worker
checks for up to five minutes after reconnecting.

Run from blackbook when a brief tailnet interruption is acceptable:

```sh
ssh rack-mini '/usr/local/bin/flox activate --dir ~/Projects/MessageVault/mcp-funnel-20261013 -- /usr/bin/python3 ~/Projects/MessageVault/mcp-funnel-20261013/restart-tailscale.py --apply'
```

Run without sudo. macOS denied the original `launchctl kickstart` attempt even
with administrator privileges; that unsupported path has been removed. The
script detaches a worker before reconnecting, so SSH can disconnect without
interrupting recovery. It waits for Tailscale, verifies the Funnel
configuration is unchanged, and checks each public relay for HTTP 401. It does
not restart msgvault services or change authentication. Results are in
`tailscale-restart.log` in the deployment root. A successful ingress check should
be followed by an authenticated MCP query. No passwordless administrator rule
is needed.

## Temporary hourly recovery check

`com.msgvault.funnel-health` is installed in
`~/Library/LaunchAgents/com.msgvault.funnel-health.plist` on rack-mini. It runs
at load and every 3,600 seconds while cdolan is logged in. It invokes the helper
with `--apply --if-unhealthy` inside the deployment's Flox environment and sets
`TAILSCALE_BE_CLI=1` so the macOS Tailscale executable runs as a CLI under launchd.

The check uses public DNS and probes each public relay. If every relay returns
HTTP 401, it exits without changing anything. A failed check is retried after
five seconds. After a second failed check, the helper verifies that the local
MCP and proxy endpoints both return HTTP 401 before queuing the detached
reconnect. If either local service is unavailable, it logs the failure and exits
without reconnecting. A reconnect briefly interrupts the mini's tailnet traffic.
It leaves the msgvault services running and preserves the Funnel configuration.

Scheduled checks are logged to `logs/funnel-health.log` in the deployment root;
queued recovery results go to `tailscale-restart.log`. The first scheduled run
passed on 2026-10-13 with both public relays healthy, exit code 0, and unchanged
service PIDs. `hourly-health-acceptance.json` records this verification.

This is a temporary mitigation with no automatic expiry. To stop it now and
keep it disabled at future logins, run on rack-mini without sudo:

```sh
launchctl disable gui/$(id -u)/com.msgvault.funnel-health
launchctl bootout gui/$(id -u)/com.msgvault.funnel-health
```

The plist and helper remain available for inspection. To re-enable the job:

```sh
launchctl enable gui/$(id -u)/com.msgvault.funnel-health
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.msgvault.funnel-health.plist
```
