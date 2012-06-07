import unittest
import tempfile
import json
from path import path


def setUpModule(self):
    global sarge
    import sarge


class WorkflowTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump({'deployments': [{'name': 'testy'}]}, f)

    def test_new_version(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        self.assertTrue(version_path.isdir())
        self.assertEqual(version_path.parent.parent, self.tmp)
