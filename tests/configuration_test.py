import unittest
import tempfile
import json
import ConfigParser
from path import path
from mock import patch


def setUpModule(self):
    global sarge
    import sarge


def read_config(cfg_path):
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


def config_file_checker(cfg_path):
    config = read_config(cfg_path)

    def eq_config(section, field, ok_value):
        cfg_value = config.get(section, field)
        msg = 'Configuration field [%s] %s\n%r != %r' % (
            section, field, cfg_value, ok_value)
        assert cfg_value == ok_value, msg

    return eq_config


class ConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    def test_enumerate_deployments(self):
        self.configure({'deployments': [{'name': 'testy'}]})

        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])

    def test_generate_supervisord_cfg_with_no_deployments(self):
        self.configure({'deployments': []})
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

    def test_generate_supervisord_cfg_with_socket_owner(self):
        self.configure({
            'supervisord_socket_owner': 'theone',
            'deployments': [],
        })
        s = sarge.Sarge(self.tmp)
        s.generate_supervisord_configuration()

        eq_config = config_file_checker(self.tmp/sarge.SUPERVISORD_CFG)

        eq_config('unix_http_server', 'chown', 'theone')

    def test_generated_cfg_ignores_deployments_with_no_versions(self):
        self.configure({'deployments': [
            {'name': 'testy', 'command': "echo starting up"},
        ]})

        s = sarge.Sarge(self.tmp)
        s.generate_supervisord_configuration()

        config = read_config(self.tmp/sarge.SUPERVISORD_CFG)
        self.assertEqual(config.sections(),
                         ['unix_http_server', 'rpcinterface:supervisor',
                          'supervisord', 'supervisorctl'])

    def test_generate_supervisord_cfg_with_deployment_command(self):
        self.configure({'deployments': [
            {'name': 'testy', 'command': "echo starting up"},
        ]})

        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        testy.activate_version(testy.new_version())

        eq_config = config_file_checker(self.tmp/sarge.SUPERVISORD_CFG)

        eq_config('program:testy', 'command', "echo starting up")
        eq_config('program:testy', 'redirect_stderr', 'true')
        eq_config('program:testy', 'startsecs', '2')

    def test_get_deployment(self):
        self.configure({'deployments': [{'name': 'testy'}]})

        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        self.assertEqual(testy.name, 'testy')

    def test_get_deployment_invalid_name(self):
        self.configure({'deployments': []})

        s = sarge.Sarge(self.tmp)
        with self.assertRaises(KeyError):
            testy = s.get_deployment('testy')

    def test_directory_updated_after_activation(self):
        self.configure({'deployments': [{'name': 'testy', 'command': 'echo'}]})
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        testy.activate_version(version_path)
        eq_config = config_file_checker(self.tmp/sarge.SUPERVISORD_CFG)
        eq_config('program:testy', 'directory', version_path)
