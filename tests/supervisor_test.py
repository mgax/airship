import sys
import ConfigParser
from path import path
from mock import call
from common import SargeTestCase


def read_config(cfg_path):
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


MISSING = object()


def config_file_checker(cfg_path):
    config = read_config(cfg_path)

    def eq_config(section, field, ok_value):
        try:
            cfg_value = config.get(section, field)
        except ConfigParser.NoOptionError:
            cfg_value = MISSING
        msg = 'Configuration field [%s] %s\n%r != %r' % (
            section, field, cfg_value, ok_value)
        assert cfg_value == ok_value, msg

    return eq_config


class SupervisorConfigurationTest(SargeTestCase):

    def setUp(self):
        self.mock_supervisorctl = self.patch('sarge.daemons.Supervisor.ctl')

    def test_generate_supervisord_cfg_with_no_deployments(self):
        self.sarge().generate_supervisord_configuration()

        config_path = self.tmp / 'etc' / 'supervisor.conf'
        eq_config = config_file_checker(config_path)

        eq_config('unix_http_server', 'file',
                  self.tmp / 'var' / 'run' / 'supervisor.sock')
        eq_config('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                  'supervisor.rpcinterface:make_main_rpcinterface')
        eq_config('supervisord', 'logfile',
                  self.tmp / 'var' / 'log' / 'supervisor.log')
        eq_config('supervisord', 'pidfile',
                  self.tmp / 'var' / 'run' / 'supervisor.pid')
        eq_config('supervisord', 'directory', self.tmp)
        eq_config('supervisorctl', 'serverurl',
                  'unix://' + self.tmp / 'var' / 'run' / 'supervisor.sock')
        eq_config('include', 'files', self.tmp / 'etc/supervisor.d/*')

    def instance_cfg(self, instance):
        return self.tmp / 'etc' / 'supervisor.d' / instance.id_

    def test_generate_supervisord_cfg_with_run_command(self):
        instance = self.sarge().new_instance()
        instance.start()

        eq_config = config_file_checker(self.instance_cfg(instance))
        section = 'program:%s' % instance.id_

        eq_config(section, 'command',
                  'bin/sarge run {0} ./server'.format(instance.id_))
        eq_config(section, 'redirect_stderr', 'true')
        eq_config(section, 'stdout_logfile',
                  self.tmp / 'var' / 'log' / (instance.id_ + '.log'))
        eq_config(section, 'startretries', '1')

    def test_instance_start_changes_autostart_to_true(self):
        instance = self.sarge().new_instance()
        instance.start()

        section = 'program:%s' % instance.id_
        eq_config = config_file_checker(self.instance_cfg(instance))
        eq_config(section, 'autostart', 'true')
        eq_config(section, 'startsecs', '2')

    def test_instance_stop_changes_autostart_to_false(self):
        instance = self.sarge().new_instance()
        instance.start()
        instance.stop()

        section = 'program:%s' % instance.id_
        eq_config = config_file_checker(self.instance_cfg(instance))
        eq_config(section, 'autostart', 'false')
        eq_config(section, 'autorestart', 'false')
        eq_config(section, 'startsecs', '0')

    def test_instance_start_triggers_supervisord_update(self):
        instance = self.sarge().new_instance()
        self.mock_supervisorctl.reset_mock()
        instance.start()
        self.assertEqual(self.mock_supervisorctl.mock_calls,
                         [call(['update'])])

    def test_instance_stop_triggers_supervisord_update(self):
        instance = self.sarge().new_instance()
        instance.start()
        self.mock_supervisorctl.reset_mock()
        instance.stop()
        self.assertEqual(self.mock_supervisorctl.mock_calls,
                         [call(['update'])])

    def test_instance_destroy_triggers_supervisord_update(self):
        instance = self.sarge().new_instance()
        instance.start()
        instance.stop()
        self.mock_supervisorctl.reset_mock()
        instance.destroy()
        self.assertEqual(self.mock_supervisorctl.mock_calls,
                         [call(['update'])])

    def test_destroy_instance_removes_its_supervisor_configuration(self):
        instance = self.sarge().new_instance()
        instance.start()
        cfg_path = self.tmp / 'etc' / 'supervisor.d' / instance.id_
        self.assertTrue(cfg_path.isfile())
        instance.destroy()
        self.assertFalse(cfg_path.isfile())


class SupervisorInvocationTest(SargeTestCase):

    def test_invoke_supervisorctl(self):
        self.mock_subprocess.reset_mock()
        self.sarge().daemons.ctl(['hello', 'world!'])
        supervisorctl_path = (path(sys.prefix).abspath() /
                              'bin' / 'supervisorctl')
        cfg_path = self.tmp / 'etc' / 'supervisor.conf'
        self.assertEqual(self.mock_subprocess.check_call.mock_calls,
                         [call([supervisorctl_path,
                                '-c', cfg_path,
                                'hello', 'world!'])])
