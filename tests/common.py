import os
import pwd
import json
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from path import path
from mock import patch
from importlib import import_module as imp


def configure_sarge(sarge_home, config):
    with open(sarge_home / imp('sarge.core').SARGE_CFG, 'wb') as f:
        json.dump(config, f)


def configure_deployment(sarge_home, config):
    core = imp('sarge.core')
    deployment_config_folder = sarge_home / core.DEPLOYMENT_CFG_DIR
    core.ensure_folder(deployment_config_folder)
    filename = config['name'] + '.yaml'
    with open(deployment_config_folder / filename, 'wb') as f:
        json.dump(config, f)


username = pwd.getpwuid(os.getuid())[0]


class SargeTestCase(unittest.TestCase):

    def sarge(self):
        return imp('sarge').Sarge(self.tmp)

    def patch(self, name):
        p = patch(name)
        mock_ob = p.start()
        self.addCleanup(p.stop)
        return mock_ob

    def _pre_setup(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        self.mock_subprocess = self.patch('sarge.core.subprocess')

    def __call__(self, result=None):
        self._pre_setup()
        super(SargeTestCase, self).__call__(result)
