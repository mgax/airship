import unittest
import tempfile
import json
import ConfigParser
from path import path


class ConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def test_enumerate_deployments(self):
        import sarge
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump({'deployments': [{'name': 'testy'}]}, f)

        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])

    def test_generate_supervisord_cfg_with_no_deployments(self):
        import sarge
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump({'deployments': []}, f)
        s = sarge.Sarge(self.tmp)
        s.generate_supervisord_configuration()
        config = ConfigParser.RawConfigParser()
        config.read([self.tmp/sarge.SUPERVISORD_CFG])

        def eq_config(section, field, ok_value):
            cfg_value = config.get(section, field)
            msg = 'Configuration field [%s] %s\n%r != %r' % (
                section, field, cfg_value, ok_value)
            self.assertEqual(cfg_value, ok_value, msg)

        eq_config('unix_http_server', 'file', self.tmp/'supervisord.sock')
        eq_config('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                  'supervisor.rpcinterface:make_main_rpcinterface')
        eq_config('supervisord', 'logfile', self.tmp/'supervisord.log')
        eq_config('supervisord', 'pidfile', self.tmp/'supervisord.pid')
        eq_config('supervisord', 'directory', self.tmp)
        eq_config('supervisorctl', 'serverurl',
                  'unix://' + self.tmp/'supervisord.sock')

    def test_generate_supervisord_cfg_with_deployment_command(self):
        import sarge
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            depl_config = {'name': 'testy', 'command': "echo starting up"}
            json.dump({'deployments': [depl_config]}, f)

        s = sarge.Sarge(self.tmp)
        s.generate_supervisord_configuration()
        config = ConfigParser.RawConfigParser()
        config.read([self.tmp/sarge.SUPERVISORD_CFG])

        def eq_config(section, field, ok_value):
            cfg_value = config.get(section, field)
            msg = 'Configuration field [%s] %s\n%r != %r' % (
                section, field, cfg_value, ok_value)
            self.assertEqual(cfg_value, ok_value, msg)

        eq_config('program:testy', 'command', "echo starting up")
        eq_config('program:testy', 'redirect_stderr', 'true')
        eq_config('program:testy', 'startsecs', '2')
