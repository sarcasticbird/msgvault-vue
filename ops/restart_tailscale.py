#!/usr/bin/env python3
"""Reconnect rack-mini's Tailscale client in a detached process. Run without sudo."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path('/Users/cdolan/Projects/MessageVault/mcp-funnel-20261013')
TS = '/Applications/Tailscale.app/Contents/MacOS/Tailscale'
HOST = 'rack-mini.tail659d03.ts.net'
LOG = logging.getLogger(__name__)


def event(name: str, **fields: object) -> None:
    LOG.info(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                         'event': name, **fields}))


def command(args: list[str], timeout: int = 10) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed ({result.returncode}): {result.stderr.strip()}')
    return result.stdout


def reconnect() -> None:
    try:
        command([TS, 'down', '--accept-risk=lose-ssh'], timeout=20)
    finally:
        # Recovery must still run if disconnect reports an error after it starts.
        command([TS, 'up'], timeout=60)


def public_addresses() -> list[str]:
    request = urllib.request.Request(
        f'https://cloudflare-dns.com/dns-query?name={HOST}&type=A',
        headers={'Accept': 'application/dns-json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        addresses = [answer['data'] for answer in json.load(response).get('Answer', [])
                     if answer['type'] == 1]
    if not addresses:
        raise RuntimeError('Public DNS returned no Funnel IPv4 addresses')
    return addresses


def probe(addresses: list[str]) -> list[dict[str, object]]:
    results = []
    for address in addresses:
        result = subprocess.run([
            '/usr/bin/curl', '--silent', '--show-error', '--max-time', '8',
            '--resolve', f'{HOST}:443:{address}', '-o', '/dev/null', '-w', '%{http_code}',
            f'https://{HOST}/mcp'], capture_output=True, text=True, timeout=10)
        results.append({'relay': address, 'exit': result.returncode,
                        'http': result.stdout, 'error': result.stderr.strip()})
    return results


def needs_reconnect(addresses: list[str]) -> bool:
    for attempt in range(2):
        checks = probe(addresses)
        event('scheduled_probe', attempt=attempt + 1, checks=checks)
        if checks and all(item['exit'] == 0 and item['http'] == '401' for item in checks):
            return False
        if attempt == 0:
            time.sleep(5)
    return True


def local_services_healthy() -> bool:
    checks = []
    for name, port in [('mcp', 8081), ('proxy', 8082)]:
        args = ['/usr/bin/curl', '--silent', '--show-error', '--max-time', '8',
                '-o', '/dev/null', '-w', '%{http_code}']
        if name == 'proxy':
            args += ['--header', f'Host: {HOST}']
        args += [f'http://127.0.0.1:{port}/mcp']
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        checks.append({'service': name, 'exit': result.returncode,
                       'http': result.stdout, 'error': result.stderr.strip()})
    event('local_service_probe', checks=checks)
    return all(item['exit'] == 0 and item['http'] == '401' for item in checks)


def snapshot() -> dict[str, object]:
    state = json.loads(command([TS, 'status', '--json']))
    if state.get('Self', {}).get('DNSName', '').rstrip('.') != HOST:
        raise RuntimeError('This script is only for rack-mini')
    return {'funnel': json.loads(command([TS, 'funnel', 'status', '--json'])),
            'addresses': public_addresses()}


def worker() -> int:
    os.umask(0o077)
    with (ROOT / 'tailscale-reconnect.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = snapshot()
        event('restart_starting', method='tailscale down/up')
        time.sleep(2)  # Let the initiating SSH command return before disconnecting.
        reconnect()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                state = json.loads(command([TS, 'status', '--json'], timeout=5))
                if state.get('BackendState') == 'Running':
                    break
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                event('waiting_for_tailscale', error=str(error))
            time.sleep(2)
        else:
            raise RuntimeError('Tailscale did not report Running within 60 seconds')
        after = snapshot()
        if after['funnel'] != before['funnel']:
            raise RuntimeError('Funnel configuration changed; inspect before restoring it')
        checks = []
        deadline = time.monotonic() + 300
        attempt = 0
        while True:
            attempt += 1
            checks = probe(after['addresses'])
            event('public_probe', attempt=attempt, checks=checks)
            if all(item['exit'] == 0 and item['http'] == '401' for item in checks):
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(10)
        passed = all(item['exit'] == 0 and item['http'] == '401' for item in checks)
        event('restart_complete', public_ingress_recovered=passed,
              funnel_config_preserved=True)
        return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Queues a detached reconnect; no sudo')
    parser.add_argument('--if-unhealthy', action='store_true',
                        help='With --apply, reconnect only after two failed public checks')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.if_unhealthy and not args.apply:
        parser.error('--if-unhealthy requires --apply')
    if os.geteuid() == 0:
        raise RuntimeError('Run as cdolan without sudo; no administrator access is needed')
    if args.worker:
        return worker()
    before = snapshot()
    event('preflight', **before, requires_administrator=False, detached=True,
          reconnect_commands=[[TS, 'down', '--accept-risk=lose-ssh'], [TS, 'up']])
    if not args.apply:
        event('dry_run_complete', checks=probe(before['addresses']), changes_made=False)
        return 0
    if args.if_unhealthy and not needs_reconnect(before['addresses']):
        event('healthy_no_reconnect', changes_made=False)
        return 0
    if args.if_unhealthy and not local_services_healthy():
        event('local_services_unhealthy_no_reconnect', changes_made=False)
        return 1
    os.umask(0o077)
    logfile = ROOT / 'tailscale-restart.log'
    with logfile.open('ab') as output:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker'],
                                 stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                 start_new_session=True)
    event('restart_queued', pid=child.pid, logfile=str(logfile))
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        event('restart_failed', error=str(error))
        sys.exit(1)
