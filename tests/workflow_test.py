import unittest
import tempfile
import json
from path import path
from mock import patch, call


def setUpModule(self):
    global sarge
    import sarge


class WorkflowTest(unittest.TestCase):

    def setUp(self):
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump({'deployments': [{'name': 'testy', 'command': 'K'}]}, f)

    def test_new_version(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        self.assertTrue(version_path.isdir())
        self.assertEqual(version_path.parent.parent, self.tmp)

    def test_versions_have_different_paths(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path_1 = path(testy.new_version())
        version_path_2 = path(testy.new_version())
        self.assertNotEqual(version_path_1, version_path_2)

    def test_activation_triggers_supervisord_reread(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())

        self.mock_supervisorctl.reset_mock()
        testy.activate_version(version_path)
        self.assertIn(call(['reread']), self.mock_supervisorctl.mock_calls)

    def test_start_deployment_invokes_supervisorctl_start(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        testy.activate_version(version_path)

        self.mock_supervisorctl.reset_mock()
        testy.start()
        self.assertIn(call(['start', 'testy']),
                      self.mock_supervisorctl.mock_calls)
