import os
import sys
import subprocess
from path import path
from mock import patch, call
from common import AirshipTestCase


src_dir = path(__file__).parent.parent


class RealProcessTest(AirshipTestCase):

    def setUp(self):
        if os.environ.get('SKIPSLOW'):
            from nose import SkipTest
            raise SkipTest
        cfg_path = self.tmp / 'etc' / 'airship.yaml'
        cfg_path.write_text('{}')
        bin_path = self.tmp / 'airshipbin'
        bin_path.write_text('#!{0}\nfrom airship.core import main\nmain()\n'
                            .format(sys.executable))
        bin_path.chmod(0755)

    def airshipbin(self, *args, **kwargs):
        argv = ['./airshipbin', '.'] + list(args)
        stdin = kwargs.pop('stdin', '')
        assert not kwargs
        env = dict(os.environ,
                   PYTHONPATH=src_dir,
                   AIRSHIP_NO_SUPERVISORCTL='y')
        p = subprocess.Popen(argv, cwd=self.tmp,
                             env=env,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        return p.communicate(stdin)[0]

    def test_bucket_run_opens_shell_which_executes_commands(self):
        bucket_id = self.airshipbin('new', '{}').strip()
        directory = self.airshipbin('run', bucket_id, stdin="pwd\n").strip()
        self.assertEqual(directory, (self.tmp / bucket_id).realpath())

    def test_bucket_run_with_arguments_executes_them_in_shell(self):
        bucket_id = self.airshipbin('new', '{}').strip()
        directory = self.airshipbin('run', bucket_id, 'pwd').strip()
        self.assertEqual(directory, (self.tmp / bucket_id).realpath())

    def test_shell_loads_rc_file(self):
        from airship.core import RUN_RC_NAME
        bucket_id = self.airshipbin('new', '{}').strip()
        (self.tmp / bucket_id / RUN_RC_NAME).write_text("MYVAR='asdf'\n")
        out = self.airshipbin('run', bucket_id, "echo $MYVAR").strip()
        self.assertEqual(out, "asdf")
