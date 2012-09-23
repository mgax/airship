import os
import sys
import subprocess
from path import path
from mock import patch, call
from common import SargeTestCase


src_dir = path(__file__).parent.parent


def setUpModule():
    if os.environ.get('SKIPSLOW'):
        from nose import SkipTest
        raise SkipTest


class ShellTest(SargeTestCase):

    def setUp(self):
        cfg_path = self.tmp / 'etc' / 'sarge.yaml'
        cfg_path.write_text('{}')
        bin_path = self.tmp / 'sargebin'
        bin_path.write_text('#!{0}\nfrom sarge.core import main\nmain()\n'
                            .format(sys.executable))
        bin_path.chmod(0755)

    def sargebin(self, *args, **kwargs):
        argv = ['./sargebin', '.'] + list(args)
        stdin = kwargs.pop('stdin', '')
        assert not kwargs
        env = dict(os.environ, PYTHONPATH=src_dir, SARGE_NO_SUPERVISORCTL='y')
        p = subprocess.Popen(argv, cwd=self.tmp,
                             env=env,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        return p.communicate(stdin)[0]

    def test_instance_run_opens_shell_which_executes_commands(self):
        instance_id = self.sargebin('new', '{}').strip()
        directory = self.sargebin('run', instance_id, stdin="pwd\n").strip()
        self.assertEqual(directory, (self.tmp / instance_id).realpath())

    def test_instance_run_with_arguments_executes_them_in_shell(self):
        instance_id = self.sargebin('new', '{}').strip()
        directory = self.sargebin('run', instance_id, 'pwd').strip()
        self.assertEqual(directory, (self.tmp / instance_id).realpath())

    def test_shell_loads_rc_file(self):
        from sarge.core import RUN_RC_NAME
        instance_id = self.sargebin('new', '{}').strip()
        (self.tmp / instance_id / RUN_RC_NAME).write_text("MYVAR='asdf'\n")
        out = self.sargebin('run', instance_id, "echo $MYVAR").strip()
        self.assertEqual(out, "asdf")
