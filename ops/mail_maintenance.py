#!/usr/bin/env python3
"""Apple Mail mirror maintenance for a stock msgvault v0.21 daemon."""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import plistlib
import signal
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

LOG = logging.getLogger('msgvault-mail')
TRASH_SQL = '''EXISTS (
    SELECT 1 FROM message_labels ml JOIN labels l ON l.id=ml.label_id
    WHERE ml.message_id=m.id AND (
      l.source_label_id IN ('TRASH','SPAM')
      OR l.name IN ('Trash','Spam','Junk','Deleted Messages')
      OR l.name LIKE '%/Trash' OR l.name LIKE '%/Spam'
      OR l.name LIKE '%/Junk' OR l.name LIKE '%/Deleted Messages'))'''


@dataclass(frozen=True)
class CleanupPlan:
    orphans: tuple[int, ...]
    trash: tuple[int, ...]
    changed: bool = False


@contextmanager
def file_lock(path: Path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f'Archive is owned or busy: {path.name}') from error
        yield
    finally:
        os.close(fd)


@contextmanager
def archive_locks(home: Path):
    # Match msgvault's lock ordering, including the daemon-start lease.
    with file_lock(home/'daemon.lock'), file_lock(home/'db.write.lock'):
        yield


def scan_mail(mail: Path) -> set[str]:
    if not mail.is_dir():
        raise ValueError('Mail directory is missing')
    hashes = set()
    def failed_walk(error):
        raise error
    for directory, _, filenames in os.walk(mail, onerror=failed_walk):
        for filename in filenames:
            if not filename.endswith('.emlx'):
                continue
            path = Path(directory)/filename
            with path.open('rb') as handle:
                length = int(handle.readline().strip())
                if length <= 0:
                    raise ValueError(f'Invalid EMLX length: {path}')
                remaining = length
                digest = hashlib.sha256()
                while remaining:
                    chunk = handle.read(min(remaining, 1024*1024))
                    if not chunk:
                        raise ValueError(f'Truncated EMLX length: {path}')
                    digest.update(chunk)
                    remaining -= len(chunk)
            hashes.add('emlx-'+digest.hexdigest())
    if not hashes:
        raise ValueError('Mail tree is empty; no EMLX files found. Refusing reconciliation.')
    return hashes


def connect(home: Path, *, readonly: bool):
    database = home/'msgvault.db'
    return sqlite3.connect(database.resolve().as_uri()+('?mode=ro' if readonly else '?mode=rw'),
                           uri=True, timeout=5)


def plan_cleanup(db, hashes: set[str] | None, mode: str) -> CleanupPlan:
    orphans = ()
    if mode == 'reconcile':
        if not hashes:
            raise ValueError('Refusing reconciliation with an empty Mail hash set')
        orphans = tuple(row[0] for row in db.execute('''SELECT id,source_message_id FROM messages
            WHERE source_message_id LIKE 'emlx-%' AND deleted_from_source_at IS NULL ORDER BY id''')
            if row[1] not in hashes)
    active_only = ' AND m.deleted_from_source_at IS NULL' if mode == 'reconcile' else ''
    trash = tuple(row[0] for row in db.execute('SELECT m.id FROM messages m WHERE '+TRASH_SQL+active_only+' ORDER BY m.id'))
    return CleanupPlan(orphans, trash)


def preview(home: Path, hashes: set[str] | None, mode: str) -> CleanupPlan:
    with closing(connect(home, readonly=True)) as db:
        return plan_cleanup(db, hashes, mode)


def apply_cleanup(home: Path, hashes: set[str] | None, mode: str) -> CleanupPlan:
    with archive_locks(home), closing(connect(home, readonly=False)) as db, db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        plan = plan_cleanup(db, hashes, mode)
        if mode == 'reconcile':
            identifiers = sorted(set(plan.orphans) | set(plan.trash))
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            db.executemany('UPDATE messages SET deleted_from_source_at=? WHERE id=? AND deleted_from_source_at IS NULL',
                           ((timestamp, ident) for ident in identifiers))
        else:
            identifiers = list(plan.trash)
            # Match native GC: preserve reply messages when their parent is
            # removed, and delete FTS entries which have no foreign-key cascade.
            db.executemany('UPDATE messages SET reply_to_message_id=NULL WHERE reply_to_message_id=?',
                           ((ident,) for ident in identifiers))
            if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',
                          ('table','messages_fts')).fetchone():
                db.executemany('DELETE FROM messages_fts WHERE rowid=?',
                               ((ident,) for ident in identifiers))
            db.executemany('DELETE FROM messages WHERE id=?', ((ident,) for ident in identifiers))
        if identifiers:
            # Existing-row repairs must invalidate already-exported Parquet rows.
            db.execute('''INSERT INTO archive_metadata(key,value) VALUES(?, '1')
                ON CONFLICT(key) DO UPDATE SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT)''',
                       ('derived_data_revision',))
        return CleanupPlan(plan.orphans, plan.trash, bool(identifiers))


@contextmanager
def paused_service(service):
    try:
        service.stop()
        yield
    finally:
        service.start()


class LaunchdService:
    def __init__(self, plist: Path, home: Path):
        self.plist = plist.resolve(strict=True)
        with self.plist.open('rb') as handle:
            definition = plistlib.load(handle)
        args = definition['ProgramArguments']
        try:
            configured_home = Path(args[args.index('--home')+1]).resolve()
        except (ValueError, IndexError) as error:
            raise ValueError('Managed service must specify --home explicitly') from error
        if configured_home != home.resolve():
            raise ValueError('Service archive does not match requested archive')
        self.home = home
        self.domain = f'gui/{os.getuid()}'
        self.target = self.domain+'/'+definition['Label']
        self.bootout_requested = False

    def stop(self):
        subprocess.run(['/bin/launchctl','print',self.target],check=True,stdout=subprocess.DEVNULL)
        # Record intent before launchctl: interruption can happen while bootout
        # is still removing the job and print continues to report it loaded.
        self.bootout_requested = True
        subprocess.run(['/bin/launchctl','bootout',self.target],check=True)
        # bootout returns while launchd is still removing the service and while
        # the daemon may still own its locks. Wait for both before any SQL write.
        deadline = time.monotonic()+60
        while time.monotonic() < deadline:
            state = subprocess.run(['/bin/launchctl','print',self.target],
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if state.returncode != 0:
                try:
                    with archive_locks(self.home):
                        return
                except RuntimeError:
                    LOG.info('waiting_for_archive_owner_exit')
            time.sleep(.1)
        raise RuntimeError('Managed daemon did not finish stopping within 60 seconds')

    def start(self):
        deadline = time.monotonic()+60
        while True:
            state = subprocess.run(['/bin/launchctl','print',self.target],
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if state.returncode != 0:
                break
            if not self.bootout_requested:
                # A failed stop before bootout can leave the original job loaded.
                return
            if time.monotonic() >= deadline:
                raise RuntimeError('Managed service removal did not finish before restoration')
            time.sleep(.1)
        subprocess.run(['/bin/launchctl','bootstrap',self.domain,str(self.plist)],check=True)
        self.bootout_requested = False


def cli_command(args, *command):
    return [str(args.binary), '--local', '--home', str(args.home),
            '--config', str(args.home/'config.toml'), *command]


def rebuild_cache(args):
    # launchd bootstrap also returns before the new daemon serves requests.
    # Wait instead of allowing the CLI to race startup and try to claim a daemon.
    url = os.environ['MSGVAULT_API_URL'].rstrip('/')+'/health'
    deadline = time.monotonic()+120
    while True:
        try:
            with urllib.request.urlopen(url,timeout=2) as response:
                if response.status == 200:
                    break
        except (urllib.error.URLError,TimeoutError):
            LOG.debug('managed_daemon_not_ready')
        if time.monotonic() >= deadline:
            raise RuntimeError('Managed daemon did not become ready within 120 seconds')
        time.sleep(.25)
    # The daemon handles this command and publishes the rebuilt cache atomically.
    subprocess.run(cli_command(args,'build-cache','--full-rebuild'),check=True,timeout=600)


def maintain(args):
    hashes = scan_mail(args.mail_dir) if args.operation == 'reconcile' else None
    plan = preview(args.home,hashes,args.operation)
    LOG.info('cleanup_plan',extra={'facts':{'operation':args.operation,'orphans':len(plan.orphans),
             'trash':len(plan.trash),'apply':args.apply}})
    if not args.apply or not (plan.orphans or plan.trash):
        return
    if args.service_plist:
        with paused_service(LaunchdService(args.service_plist,args.home)):
            result = apply_cleanup(args.home,hashes,args.operation)
        if result.changed:
            rebuild_cache(args)
    else:
        # Offline use is safe only if neither daemon nor writer owns the archive.
        result = apply_cleanup(args.home,hashes,args.operation)
    LOG.info('cleanup_complete',extra={'facts':{'operation':args.operation,'changed':result.changed}})


def import_mail(args):
    if not args.identifier or not args.service_plist:
        raise ValueError('Import requires --identifier and --service-plist')
    if not args.skip_sync:
        remote = os.environ.get('MSGVAULT_MAIL_REMOTE_HOST','blackbook.tail659d03.ts.net')
        user = os.environ.get('MSGVAULT_MAIL_REMOTE_USER',os.environ.get('USER','cdolan'))
        deadline = time.monotonic()+300
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise RuntimeError('Mail source is not reachable after 300 seconds')
            try:
                probe = subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=2',
                                        user+'@'+remote,'true'], stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL,timeout=min(5,remaining))
                if probe.returncode == 0:
                    break
            except subprocess.TimeoutExpired:
                LOG.info('mail_source_probe_timeout')
            time.sleep(min(5,max(0,deadline-time.monotonic())))
        args.mail_dir.mkdir(parents=True,exist_ok=True)
        subprocess.run(['rsync','-a','--delete','--exclude=Trash.mbox','--exclude=Spam.mbox',
                        '--exclude=Junk.mbox','--exclude=Deleted Messages.mbox',
                        user+'@'+remote+':'+os.environ.get('MSGVAULT_MAIL_REMOTE_PATH','Library/Mail/'),
                        str(args.mail_dir)+'/'],check=True,timeout=600)
        if not (args.mail_dir/'V10').is_dir():
            raise ValueError('V10 Mail directory is missing after sync')
    # Validate the mirror before importing or making cleanup decisions.
    scan_mail(args.mail_dir)
    subprocess.run(cli_command(args,'import-emlx',str(args.mail_dir),'--identifier',args.identifier,
                               '--no-resume'),check=True,timeout=1200)
    args.operation = 'reconcile'
    args.apply = True
    maintain(args)


class JsonLog(logging.Formatter):
    def format(self, record):
        return json.dumps({'time':datetime.now(timezone.utc).isoformat(),'level':record.levelname,
                           'event':record.getMessage(),**getattr(record,'facts',{})})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['reconcile','purge-trash','import'])
    parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--mail-dir',type=Path)
    parser.add_argument('--service-plist',type=Path)
    parser.add_argument('--identifier')
    parser.add_argument('--apply',action='store_true',help='Default is a read-only cleanup plan')
    parser.add_argument('--skip-sync',action='store_true',help='Import an existing local mirror without rsync')
    args = parser.parse_args()
    args.home = args.home.resolve(strict=True)
    args.binary = args.binary.resolve(strict=True)
    if args.operation in ('reconcile','import') and args.mail_dir is None:
        parser.error('--mail-dir is required')
    if args.service_plist and not os.environ.get('MSGVAULT_API_URL'):
        parser.error('MSGVAULT_API_URL is required for managed service readiness checks')
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLog())
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)
    def interrupted(signum, _frame):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted)
    try:
        with file_lock(args.home/'mail-pipeline.lock'):
            if args.operation == 'import':
                import_mail(args)
            else:
                maintain(args)
    except Exception as error:
        LOG.error('maintenance_failed',extra={'facts':{'error':str(error)}})
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
