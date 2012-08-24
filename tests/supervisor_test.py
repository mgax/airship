import sys
import ConfigParser
from path import path
from mock import call
from common import configure_deployment, imp
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

    def test_generate_supervisord_cfg_with_no_deployments(self):
        self.sarge().generate_supervisord_configuration()

        config_path = self.tmp / imp('sarge.core').SUPERVISORD_CFG
        eq_config = config_file_checker(config_path)

        eq_config('unix_http_server', 'file', self.tmp / 'supervisord.sock')
        eq_config('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                  'supervisor.rpcinterface:make_main_rpcinterface')
        eq_config('supervisord', 'logfile', self.tmp / 'supervisord.log')
        eq_config('supervisord', 'pidfile', self.tmp / 'supervisord.pid')
        eq_config('supervisord', 'directory', self.tmp)
        eq_config('supervisorctl', 'serverurl',
                  'unix://' + self.tmp / 'supervisord.sock')
        eq_config('include', 'files', 'active/*/supervisor_deploy.conf')

    def test_generate_supervisord_cfg_with_deployment_command(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [{'command': "echo starting up", 'name': 'tprog'}],
        })
        testy = self.sarge().get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)

        run_folder = path(version_folder + '.run')
        cfg_folder = path(version_folder + '.cfg')
        config_path = cfg_folder / imp('sarge.core').SUPERVISOR_DEPLOY_CFG
        eq_config = config_file_checker(config_path)

        eq_config('program:testy_tprog', 'command', "echo starting up")
        eq_config('program:testy_tprog', 'redirect_stderr', 'true')
        eq_config('program:testy_tprog', 'stdout_logfile',
                  run_folder / 'stdout.log')
        eq_config('program:testy_tprog', 'startsecs', '2')
        eq_config('program:testy_tprog', 'autostart', 'false')
        eq_config('program:testy_tprog', 'environment',
                  'SARGEAPP_CFG="%s"' % (cfg_folder /
                                         imp('sarge.core').APP_CFG))

    def test_supervisor_cfg_defines_group(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [
                {'command': "echo 1", 'name': 'tprog1'},
                {'command': "echo 2", 'name': 'tprog2'},
            ],
        })
        testy = self.sarge().get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        cfg_path = cfg_folder / imp('sarge.core').SUPERVISOR_DEPLOY_CFG
        eq_config = config_file_checker(cfg_path)

        eq_config('group:testy', 'programs', "testy_tprog1,testy_tprog2")

    def test_get_deployment_invalid_name(self):
        with self.assertRaises(KeyError):
            self.sarge().get_deployment('testy')

    def test_directory_updated_after_activation(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [{'command': 'echo', 'name': 'tprog'}],
        })
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        cfg_path = cfg_folder / imp('sarge.core').SUPERVISOR_DEPLOY_CFG
        eq_config = config_file_checker(cfg_path)
        eq_config('program:testy_tprog', 'directory', version_folder)


class SupervisorInvocationTest(SargeTestCase):

    def test_invoke_supervisorctl(self):
        self.mock_subprocess.reset_mock()
        self.sarge().daemons.ctl(['hello', 'world!'])
        supervisorctl_path = (path(sys.prefix).abspath() /
                              'bin' / 'supervisorctl')
        cfg_path = self.tmp / imp('sarge.core').SUPERVISORD_CFG
        self.assertEqual(self.mock_subprocess.check_call.mock_calls,
                         [call([supervisorctl_path,
                                '-c', cfg_path,
                                'hello', 'world!'])])
