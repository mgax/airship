from utils import unittest
import tempfile
import json
import sys
import ConfigParser
from path import path
from mock import patch, call
from utils import configure_sarge, configure_deployment, username


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


def read_config(cfg_path):
    import ConfigParser
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


class SupervisorConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        configure_sarge(self.tmp, {})

    def test_generate_supervisord_cfg_with_no_deployments(self):
        s = sarge.Sarge(self.tmp)
        s.generate_supervisord_configuration()

        eq_config = config_file_checker(self.tmp/sarge.SUPERVISORD_CFG)

        eq_config('unix_http_server', 'file', self.tmp/'supervisord.sock')
        eq_config('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                  'supervisor.rpcinterface:make_main_rpcinterface')
        eq_config('supervisord', 'logfile', self.tmp/'supervisord.log')
        eq_config('supervisord', 'pidfile', self.tmp/'supervisord.pid')
        eq_config('supervisord', 'directory', self.tmp)
        eq_config('supervisorctl', 'serverurl',
                  'unix://' + self.tmp/'supervisord.sock')
        eq_config('include', 'files', 'active/*/supervisor_deploy.conf')

    def test_generated_cfg_ignores_deployments_with_no_versions(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        s.generate_supervisord_configuration()

        config = read_config(self.tmp/sarge.SUPERVISORD_CFG)
        self.assertItemsEqual(config.sections(),
                              ['unix_http_server', 'rpcinterface:supervisor',
                               'supervisord', 'supervisorctl', 'include'])

    def test_generate_supervisord_cfg_with_deployment_command(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [{'command': "echo starting up", 'name': 'tprog'}],
            'user': username,
        })
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)

        run_folder = path(version_folder + '.run')
        cfg_folder = path(version_folder + '.cfg')
        eq_config = config_file_checker(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)

        eq_config('program:testy_tprog', 'command', "echo starting up")
        eq_config('program:testy_tprog', 'redirect_stderr', 'true')
        eq_config('program:testy_tprog', 'stdout_logfile', run_folder/'stdout.log')
        eq_config('program:testy_tprog', 'startsecs', '2')
        eq_config('program:testy_tprog', 'autostart', 'false')
        eq_config('program:testy_tprog', 'autorestart', MISSING)

    def test_supervisor_cfg_is_empty_if_version_needs_no_programs(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)
        cfg_folder = path(version_folder + '.cfg')
        supervisor_deploy_cfg = cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG
        self.assertEqual(supervisor_deploy_cfg.text().strip(),
                         "[group:testy]\nprograms =")

    def test_supervisor_cfg_defines_group(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [
                {'command': "echo 1", 'name': 'tprog1'},
                {'command': "echo 2", 'name': 'tprog2'},
            ],
            'user': username,
        })
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        eq_config = config_file_checker(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)

        eq_config('group:testy', 'programs', "testy_tprog1,testy_tprog2")

    def test_autorestart_option(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [{'command': 'echo', 'name': 'tprog'}],
            'autorestart': 'always',
            'user': username,
        })
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        eq_config = config_file_checker(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)

        eq_config('program:testy_tprog', 'autorestart', 'true')

    def test_user_option(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'programs': [{'command': 'echo', 'name': 'tprog'}],
            'user': 'someone',
        })
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        eq_config = config_file_checker(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)

        eq_config('program:testy_tprog', 'user', 'someone')

    def test_get_deployment(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        self.assertEqual(testy.name, 'testy')

    def test_get_deployment_invalid_name(self):
        s = sarge.Sarge(self.tmp)
        with self.assertRaises(KeyError):
            testy = s.get_deployment('testy')

    def test_directory_updated_after_activation(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'user': username,
            'programs': [{'command': 'echo', 'name': 'tprog'}],
        })
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        eq_config = config_file_checker(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)
        eq_config('program:testy_tprog', 'directory', version_folder)

    def test_shared_programs_list_generates_program_config_entry(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        @s.on_activate_version.connect
        def define_program(depl, share, **extra):
            share['programs'].append({
                'name': 'theone',
                'command': 'echo',
            })
        testy = s.get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        eq_config = config_file_checker(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)
        eq_config('program:testy_theone', 'directory', version_folder)
        eq_config('program:testy_theone', 'command', 'echo')


class SupervisorInvocationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        configure_sarge(self.tmp, {})

    def test_invoke_supervisorctl(self):
        mock_subprocess.reset_mock()
        s = sarge.Sarge(self.tmp)
        s.supervisorctl(['hello', 'world!'])
        supervisorctl_path = path(sys.prefix).abspath()/'bin'/'supervisorctl'
        self.assertEqual(mock_subprocess.check_call.mock_calls,
                         [call([supervisorctl_path,
                                '-c', self.tmp/sarge.SUPERVISORD_CFG,
                                'hello', 'world!'])])
