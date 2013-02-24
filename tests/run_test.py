import os
from contextlib import contextmanager
from collections import namedtuple
from mock import patch
from common import AirshipTestCase


@contextmanager
def mock_exec():
    MockCall = namedtuple('MockCall', ['procname', 'args', 'environ'])
    calls = []

    def mock_execve(procname, args, environ):
        calls.append(MockCall(procname, args, environ))

    with patch('airship.core.os') as mock_os:
        mock_os.environ = os.environ
        mock_os.execve.side_effect = mock_execve
        yield calls


class MockProcessTest(AirshipTestCase):

    def test_run_prepares_environ_from_etc_app_config(self):
        env = {'SOME_CONFIG_VALUE': "hello there!"}
        bucket = self.create_airship({'env': env}).new_bucket()
        with mock_exec() as calls:
            bucket.run(None)
        environ = calls[0].environ
        self.assertEqual(environ['SOME_CONFIG_VALUE'], "hello there!")

    def test_run_inserts_port_in_environ(self):
        THING_PROC = "run the 'thing' process"
        bucket = self.create_airship({'port_map': {'thing': 13}}).new_bucket()
        bucket.process_types = {'thing': THING_PROC}
        with mock_exec() as calls:
            bucket.run('thing')
        self.assertEqual(calls[0].environ['PORT'], '13')

    def test_run_starts_process_from_list(self):
        THING_PROC = "run the 'thing' process"
        bucket = self.create_airship().new_bucket()
        bucket.process_types = {'thing': THING_PROC}
        with mock_exec() as calls:
            bucket.run('thing')
        self.assertEqual(calls[0].args[-1], THING_PROC)
