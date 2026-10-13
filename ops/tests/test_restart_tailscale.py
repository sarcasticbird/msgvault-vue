import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'restart_tailscale', Path(__file__).parents[1] / 'restart_tailscale.py')
restart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restart)


class ReconnectSafetyTests(unittest.TestCase):
    def test_local_service_failure_does_not_queue_a_scheduled_reconnect(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(restart, 'ROOT', Path(directory)), \
                patch.object(sys, 'argv', ['restart-tailscale.py', '--apply', '--if-unhealthy']), \
                patch.object(restart.os, 'geteuid', return_value=501), \
                patch.object(restart, 'snapshot', return_value={'addresses': ['a', 'b']}), \
                patch.object(restart, 'probe', return_value=[{'exit': 0, 'http': '502'}]), \
                patch.object(restart.time, 'sleep'), \
                patch.object(restart.subprocess, 'run', return_value=
                             subprocess.CompletedProcess([], 0, '503', '')), \
                patch.object(restart.subprocess, 'Popen') as spawn:
            spawn.return_value.pid = 123
            result = restart.main()
        spawn.assert_not_called()
        self.assertEqual(result, 1)

    def test_failed_public_relays_with_healthy_local_services_queue_recovery(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(restart, 'ROOT', Path(directory)), \
                patch.object(sys, 'argv', ['restart-tailscale.py', '--apply', '--if-unhealthy']), \
                patch.object(restart.os, 'geteuid', return_value=501), \
                patch.object(restart, 'snapshot', return_value={'addresses': ['a', 'b']}), \
                patch.object(restart, 'probe', return_value=[{'exit': 35, 'http': '000'}]), \
                patch.object(restart.time, 'sleep'), \
                patch.object(restart.subprocess, 'run', return_value=
                             subprocess.CompletedProcess([], 0, '401', '')), \
                patch.object(restart.subprocess, 'Popen') as spawn:
            spawn.return_value.pid = 123
            self.assertEqual(restart.main(), 0)
        spawn.assert_called_once()

    def test_scheduled_check_does_not_interrupt_a_healthy_connection(self):
        checks = [{'exit': 0, 'http': '401'}, {'exit': 0, 'http': '401'}]
        with patch.object(sys, 'argv', ['restart-tailscale.py', '--apply', '--if-unhealthy']), \
                patch.object(restart.os, 'geteuid', return_value=501), \
                patch.object(restart, 'snapshot', return_value={'addresses': ['a', 'b']}), \
                patch.object(restart, 'probe', return_value=checks), \
                patch.object(restart.subprocess, 'Popen') as spawn:
            self.assertEqual(restart.main(), 0)
        spawn.assert_not_called()

    def test_one_transient_probe_failure_does_not_trigger_a_reconnect(self):
        failed = [{'exit': 35, 'http': '000'}]
        healthy = [{'exit': 0, 'http': '401'}]
        with patch.object(restart, 'probe', side_effect=[failed, healthy]), \
                patch.object(restart.time, 'sleep'):
            self.assertFalse(restart.needs_reconnect(['a']))

    def test_reconnect_attempts_recovery_when_disconnect_times_out(self):
        recovered = []

        def execute(args, timeout=10):
            if args[1] == 'down':
                raise subprocess.TimeoutExpired(args, timeout)
            recovered.append(True)
            return ''

        with patch.object(restart, 'command', side_effect=execute):
            with self.assertRaises(subprocess.TimeoutExpired):
                restart.reconnect()
        self.assertTrue(recovered, 'A failed disconnect must still attempt recovery')

    def test_reconnect_attempts_recovery_when_disconnect_is_rejected(self):
        recovered = []

        def execute(args, timeout=10):
            if args[1] == 'down':
                raise RuntimeError('Disconnect rejected')
            recovered.append(True)
            return ''

        with patch.object(restart, 'command', side_effect=execute):
            with self.assertRaisesRegex(RuntimeError, 'Disconnect rejected'):
                restart.reconnect()
        self.assertTrue(recovered, 'A rejected disconnect must still attempt recovery')


if __name__ == '__main__':
    unittest.main()
