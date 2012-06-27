from utils import unittest
import tempfile
from path import path
from mock import patch
from utils import configure_sarge, configure_deployment, username


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        configure_sarge(self.tmp, {})

    def test_enumerate_deployments(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])

    def test_ignore_non_yaml_files(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        cfgdir = self.tmp/sarge.DEPLOYMENT_CFG_DIR
        (cfgdir/'garbage').write_text('{}')
        self.assertItemsEqual([f.name for f in cfgdir.listdir()],
                              ['testy.yaml', 'garbage'])
        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])
