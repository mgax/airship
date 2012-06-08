import unittest
import tempfile
import json
import re
from path import path
from mock import patch


def setUpModule(self):
    global sarge
    import sarge


class NginxConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    def configure_and_activate(self, deployment_config):
        self.configure({'deployments': [deployment_config]})
        s = sarge.Sarge(self.tmp)
        deployment = s.get_deployment(deployment_config['name'])
        version_path = path(deployment.new_version())
        deployment.activate_version(version_path)
        return version_path

    def assert_equivalent(self, cfg1, cfg2):
        collapse = lambda s: re.sub('\s+', ' ', s).strip()
        self.assertEqual(collapse(cfg1), collapse(cfg2))

    def test_no_web_services_yields_blank_configuration(self):
        version_path = self.configure_and_activate({'name': 'testy'})
        with open(version_path/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf, "")
