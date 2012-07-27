import os
import pwd
import json
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from path import path


def configure_sarge(sarge_home, config):
    import sarge
    with open(sarge_home/sarge.SARGE_CFG, 'wb') as f:
        json.dump(config, f)


def configure_deployment(sarge_home, config):
    import sarge
    deployment_config_folder = sarge_home/sarge.DEPLOYMENT_CFG_DIR
    sarge.ensure_folder(deployment_config_folder)
    filename = config['name'] + '.yaml'
    with open(deployment_config_folder/filename, 'wb') as f:
        json.dump(config, f)


username = pwd.getpwuid(os.getuid())[0]


class SargeTestCase(unittest.TestCase):

    def sarge(self):
        import sarge
        return sarge.Sarge(self.tmp)

    def _pre_setup(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def __call__(self, result=None):
        self._pre_setup()
        super(SargeTestCase, self).__call__(result)
