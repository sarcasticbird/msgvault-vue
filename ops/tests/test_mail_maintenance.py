from __future__ import annotations

import fcntl
import hashlib
import plistlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mail_maintenance as maintenance


class ArchiveCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.mail = self.home / 'Mail'
        self.messages = self.mail / 'Test.mbox/Messages'
        self.messages.mkdir(parents=True)
        self.raw = b'From: test@example.invalid\n\nkeep this message\n'
        (self.messages/'1.emlx').write_bytes(str(len(self.raw)).encode()+b'\n'+self.raw)
        self.keep_hash = 'emlx-'+hashlib.sha256(self.raw).hexdigest()
        self.db = sqlite3.connect(self.home/'msgvault.db')
        self.addCleanup(self.db.close)
        self.db.executescript('''
            CREATE TABLE messages(id INTEGER PRIMARY KEY, source_message_id TEXT,
                deleted_from_source_at TEXT,
                reply_to_message_id INTEGER REFERENCES messages(id));
            CREATE TABLE labels(id INTEGER PRIMARY KEY, source_label_id TEXT, name TEXT);
            CREATE TABLE message_labels(message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                label_id INTEGER REFERENCES labels(id));
            CREATE TABLE attachments(id INTEGER PRIMARY KEY,
                message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE);
            CREATE TABLE archive_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            INSERT INTO labels VALUES(1,'INBOX','Inbox'),(2,'TRASH','Trash');
        ''')
        self.db.executemany('INSERT INTO messages(id,source_message_id,deleted_from_source_at) VALUES(?,?,?)', [
            (1,self.keep_hash,None), (2,'emlx-missing',None), (3,'emlx-trash',None),
            (4,'gmail-unrelated',None), (5,'emlx-old-deleted','2026-01-01')])
        self.db.executemany('INSERT INTO message_labels VALUES(?,?)', [(1,1),(2,1),(3,2),(4,1)])
        self.db.execute('INSERT INTO attachments VALUES(1,3)')
        self.db.commit()

    def hashes(self):
        return maintenance.scan_mail(self.mail)

    def test_stalled_source_ssh_exhausts_retry_budget_and_releases_pipeline_lock(self):
        clock = [0.0]
        probes = []

        def stalled_probe(command, **kwargs):
            timeout = kwargs.get('timeout', 0)
            probes.append(timeout)
            clock[0] += timeout
            raise subprocess.TimeoutExpired(command, timeout)

        def advance(seconds):
            clock[0] += seconds

        argv = ['mail_maintenance.py', 'import', '--home', str(self.home),
                '--binary', sys.executable, '--mail-dir', str(self.mail),
                '--identifier', 'fixture', '--service-plist', str(self.home/'serve.plist')]
        with patch.object(sys, 'argv', argv), \
                patch.dict(maintenance.os.environ, {'MSGVAULT_API_URL': 'http://127.0.0.1:8080'}), \
                patch.object(maintenance.time, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(maintenance.time, 'sleep', side_effect=advance), \
                patch.object(maintenance.subprocess, 'run', side_effect=stalled_probe), \
                patch.object(maintenance.LOG, 'addHandler'), \
                self.assertLogs(maintenance.LOG, level='INFO'):
            self.assertEqual(maintenance.main(), 1)
        self.assertGreater(len(probes), 1, 'A stalled probe must retry within the overall budget')
        self.assertTrue(all(0 < timeout <= 5 for timeout in probes))
        self.assertEqual(clock[0], 300)
        with maintenance.file_lock(self.home/'mail-pipeline.lock'):
            pass

    def test_interrupted_bootout_waits_for_removal_then_restores_service(self):
        plist = self.home/'serve.plist'
        plist.write_bytes(plistlib.dumps({'Label': 'com.msgvault.fixture',
            'ProgramArguments': ['msgvault', '--home', str(self.home), 'serve']}))
        service = maintenance.LaunchdService(plist, self.home)
        state = {'loaded': True, 'removing': False, 'pending_checks': 0}

        def launchctl(command, **_kwargs):
            if command[1] == 'print':
                if state['removing']:
                    state['pending_checks'] += 1
                    if state['pending_checks'] == 2:
                        state['loaded'] = False
                return subprocess.CompletedProcess(command, 0 if state['loaded'] else 1)
            if command[1] == 'bootout':
                state['removing'] = True
                raise SystemExit(143)
            if command[1] == 'bootstrap':
                self.assertFalse(state['loaded'], 'Restoration must wait for removal')
                state.update(loaded=True, removing=False)
                return subprocess.CompletedProcess(command, 0)
            self.fail(f'Unexpected launchctl command: {command[1]}')

        with patch.object(maintenance.subprocess, 'run', side_effect=launchctl), \
                patch.object(maintenance.time, 'sleep'):
            with self.assertRaises(SystemExit):
                with maintenance.paused_service(service):
                    self.fail('Cleanup must not run after interruption')
        self.assertFalse(state['removing'])
        self.assertTrue(state['loaded'])

    def test_dry_run_preserves_database(self):
        before = list(self.db.iterdump())
        result = maintenance.preview(self.home, self.hashes(), 'reconcile')
        self.assertEqual(result.orphans, (2,3))
        self.assertEqual(result.trash, (3,))
        self.assertEqual(list(self.db.iterdump()), before)

    def test_reconcile_marks_only_missing_emlx_and_trash(self):
        result = maintenance.apply_cleanup(self.home, self.hashes(), 'reconcile')
        self.assertTrue(result.changed)
        active = [row[0] for row in self.db.execute('SELECT id FROM messages WHERE deleted_from_source_at IS NULL ORDER BY id')]
        self.assertEqual(active, [1,4])
        self.assertEqual(self.db.execute('SELECT count(*) FROM messages').fetchone()[0],5)
        self.assertEqual(self.db.execute('SELECT value FROM archive_metadata WHERE key=?',('derived_data_revision',)).fetchone()[0],'1')
        again = maintenance.apply_cleanup(self.home, self.hashes(), 'reconcile')
        self.assertFalse(again.changed)
        self.assertEqual(self.db.execute('SELECT value FROM archive_metadata').fetchone()[0],'1')

    def test_purge_deletes_trash_and_children_without_purging_orphans(self):
        result = maintenance.apply_cleanup(self.home, None, 'purge-trash')
        self.assertTrue(result.changed)
        self.assertEqual([r[0] for r in self.db.execute('SELECT id FROM messages ORDER BY id')],[1,2,4,5])
        self.assertEqual(self.db.execute('SELECT count(*) FROM attachments').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM message_labels WHERE message_id=3').fetchone()[0],0)

    def test_active_daemon_or_writer_prevents_all_writes(self):
        for name in ['daemon.lock','db.write.lock']:
            with self.subTest(lock=name), (self.home/name).open('a') as held:
                fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
                before = list(self.db.iterdump())
                with self.assertRaisesRegex(RuntimeError,'owned|busy'):
                    maintenance.apply_cleanup(self.home,self.hashes(),'reconcile')
                self.assertEqual(list(self.db.iterdump()),before)

    def test_purge_severs_only_replies_to_deleted_trash(self):
        self.db.execute('UPDATE messages SET reply_to_message_id=3 WHERE id=1')
        self.db.execute('UPDATE messages SET reply_to_message_id=2 WHERE id=4')
        self.db.commit()
        maintenance.apply_cleanup(self.home,None,'purge-trash')
        self.assertIsNone(self.db.execute('SELECT reply_to_message_id FROM messages WHERE id=1').fetchone()[0])
        self.assertEqual(self.db.execute('SELECT reply_to_message_id FROM messages WHERE id=4').fetchone()[0],2)

    def test_purge_removes_only_deleted_messages_from_search_index(self):
        self.db.execute('CREATE VIRTUAL TABLE messages_fts USING fts5(body)')
        self.db.executemany('INSERT INTO messages_fts(rowid,body) VALUES(?,?)',[(1,'retained'),(3,'trashed')])
        self.db.commit()
        maintenance.apply_cleanup(self.home,None,'purge-trash')
        self.assertEqual(list(self.db.execute('SELECT rowid FROM messages_fts')),[(1,)])

    def test_short_partial_and_empty_mail_abort_reconciliation(self):
        (self.messages/'2.partial.emlx').write_bytes(b'100\nshort')
        with self.assertRaisesRegex(ValueError,'truncated|length'):
            self.hashes()
        (self.messages/'2.partial.emlx').unlink()
        (self.messages/'1.emlx').unlink()
        with self.assertRaisesRegex(ValueError,'empty|no .*emlx'):
            self.hashes()

    def test_database_failure_rolls_back_every_cleanup_change(self):
        self.db.execute('CREATE VIRTUAL TABLE messages_fts USING fts5(body)')
        self.db.execute("INSERT INTO messages_fts(rowid,body) VALUES(3,'trash')")
        self.db.execute('UPDATE messages SET reply_to_message_id=3 WHERE id=1')
        self.db.execute("CREATE TRIGGER reject_delete BEFORE DELETE ON messages BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        self.db.commit()
        before = list(self.db.iterdump())
        with self.assertRaises(sqlite3.DatabaseError):
            maintenance.apply_cleanup(self.home,None,'purge-trash')
        self.assertEqual(list(self.db.iterdump()),before)

    def test_managed_service_is_restored_after_cleanup_failure(self):
        events = []
        class Service:
            def stop(self): events.append('stop')
            def start(self): events.append('start')
        with self.assertRaisesRegex(RuntimeError,'fixture failure'):
            with maintenance.paused_service(Service()):
                events.append('cleanup')
                raise RuntimeError('fixture failure')
        self.assertEqual(events,['stop','cleanup','start'])

    def test_partial_stop_failure_still_restores_service(self):
        events = []
        class Service:
            def stop(self):
                events.append('stop')
                raise RuntimeError('shutdown timed out')
            def start(self): events.append('start')
        with self.assertRaisesRegex(RuntimeError,'shutdown timed out'):
            with maintenance.paused_service(Service()):
                self.fail('Cleanup must not run after a stop failure')
        self.assertEqual(events,['stop','start'])


if __name__ == '__main__':
    unittest.main()
