import unittest
import tempfile
import json
from path import path


class ConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def test_enumerate_deployments(self):
        import sarge
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump([{'name': 'testy'}], f)

        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])
