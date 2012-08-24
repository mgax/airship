import sys
import ConfigParser
from path import path
from mock import call
from common import SargeTestCase, imp


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

    def test_generate_supervisord_cfg_with_no_deployments(self):
        (self.tmp / 'etc').mkdir()
        self.sarge().generate_supervisord_configuration()

        config_path = self.tmp / 'etc' / 'supervisor.conf'
        eq_config = config_file_checker(config_path)

        eq_config('unix_http_server', 'file', self.tmp / 'supervisord.sock')
        eq_config('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                  'supervisor.rpcinterface:make_main_rpcinterface')
        eq_config('supervisord', 'logfile', self.tmp / 'supervisord.log')
        eq_config('supervisord', 'pidfile', self.tmp / 'supervisord.pid')
        eq_config('supervisord', 'directory', self.tmp)
        eq_config('supervisorctl', 'serverurl',
                  'unix://' + self.tmp / 'supervisord.sock')
        eq_config('include', 'files', self.tmp / 'etc/supervisor.d/*')

    def test_generate_supervisord_cfg_with_run_command(self):
        instance = self.sarge().new_instance()
        instance.start()

        cfg_folder = path(instance.folder + '.cfg')
        cfg_path = self.tmp / 'etc' / 'supervisor.d' / instance.id_
        eq_config = config_file_checker(cfg_path)
        section = 'program:%s_daemon' % instance.id_

        eq_config(section, 'command', 'run')
        eq_config(section, 'redirect_stderr', 'true')
        eq_config(section, 'stdout_logfile',
                  instance.run_folder / 'stdout.log')
        eq_config(section, 'startsecs', '2')
        eq_config(section, 'autostart', 'false')
        eq_config(section, 'environment',
                  'SARGEAPP_CFG="%s"' % (cfg_folder /
                                         imp('sarge.core').APP_CFG))

    def test_supervisor_cfg_defines_group(self):
        instance = self.sarge().new_instance()
        instance.start()

        cfg_folder = path(instance.folder + '.cfg')
        cfg_path = self.tmp / 'etc' / 'supervisor.d' / instance.id_
        eq_config = config_file_checker(cfg_path)

        eq_config('group:%s' % instance.id_, 'programs',
                  "%s_daemon" % instance.id_)

    def test_working_directory_is_instance_home(self):
        instance = self.sarge().new_instance()
        instance.start()

        cfg_folder = path(instance.folder + '.cfg')
        cfg_path = self.tmp / 'etc' / 'supervisor.d' / instance.id_
        eq_config = config_file_checker(cfg_path)
        eq_config('program:%s_daemon' % instance.id_, 'directory',
                  instance.folder)


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
