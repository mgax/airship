import unittest
import tempfile
import json
from StringIO import StringIO
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

    def test_activation_triggers_supervisord_restart_deployment(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())

        self.mock_supervisorctl.reset_mock()
        testy.activate_version(version_path)
        self.assertIn(call(['restart', 'testy']),
                      self.mock_supervisorctl.mock_calls)

    def test_start_deployment_invokes_supervisorctl_start(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        testy.activate_version(version_path)

        self.mock_supervisorctl.reset_mock()
        testy.start()
        self.assertIn(call(['start', 'testy']),
                      self.mock_supervisorctl.mock_calls)

    def test_stop_deployment_invokes_supervisorctl_stop(self):
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        testy.activate_version(version_path)

        self.mock_supervisorctl.reset_mock()
        testy.stop()
        self.assertIn(call(['stop', 'testy']),
                      self.mock_supervisorctl.mock_calls)

    def test_status_invokes_supervisorctl_status(self):
        s = sarge.Sarge(self.tmp)
        self.mock_supervisorctl.reset_mock()
        s.status()
        self.assertIn(call(['status']), self.mock_supervisorctl.mock_calls)


class SupervisorInvocationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        (self.tmp/sarge.DEPLOYMENT_CFG).write_bytes('{"deployments": []}')

    @patch('sarge.subprocess')
    def test_invoke_supervisorctl(self, mock_subprocess):
        s = sarge.Sarge(self.tmp)
        s.supervisorctl(['hello', 'world!'])
        self.assertEqual(mock_subprocess.check_call.mock_calls,
                         [call(['supervisorctl',
                                '-c', self.tmp/sarge.SUPERVISORD_CFG,
                                'hello', 'world!'])])


class ShellTest(unittest.TestCase):

    def setUp(self):
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    @patch('sarge.Deployment.new_version')
    def test_new_version_calls_api_method(self, mock_new_version):
        mock_new_version.return_value = "path-to-new-version"
        self.configure({'deployments': [{'name': 'testy'}]})
        mock_stdout = StringIO()
        with patch('sys.stdout', mock_stdout):
            sarge.main([str(self.tmp), 'new_version', 'testy'])
        self.assertEqual(mock_new_version.mock_calls, [call()])
        self.assertEqual(mock_stdout.getvalue().strip(), "path-to-new-version")

    @patch('sarge.Deployment.activate_version')
    def test_activate_version_calls_api_method(self, mock_activate_version):
        self.configure({'deployments': [{'name': 'testy', 'command': 'echo'}]})
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = path(testy.new_version())
        sarge.main([str(self.tmp), 'activate_version',
                    'testy', str(version_folder)])
        self.assertEqual(mock_activate_version.mock_calls,
                         [call(version_folder)])
        path_arg = mock_activate_version.mock_calls[0][1][0]
        self.assertIsInstance(path_arg, path)

    @patch('sarge.Deployment.start')
    def test_start_calls_api_method(self, mock_start):
        self.configure({'deployments': [{'name': 'testy'}]})
        sarge.main([str(self.tmp), 'start', 'testy'])
        self.assertEqual(mock_start.mock_calls, [call()])

    @patch('sarge.Deployment.stop')
    def test_stop_calls_api_method(self, mock_stop):
        self.configure({'deployments': [{'name': 'testy'}]})
        sarge.main([str(self.tmp), 'stop', 'testy'])
        self.assertEqual(mock_stop.mock_calls, [call()])

    @patch('sarge.Sarge.status')
    def test_stop_calls_api_method(self, mock_status):
        self.configure({'deployments': []})
        sarge.main([str(self.tmp), 'status'])
        self.assertEqual(mock_status.mock_calls, [call()])

    def test_init_creates_configuration(self):
        self.configure({'deployments': []})
        self.assertItemsEqual([f.name for f in self.tmp.listdir()],
                              [sarge.DEPLOYMENT_CFG])
        sarge.main([str(self.tmp), 'init'])
        self.assertItemsEqual([f.name for f in self.tmp.listdir()],
                              [sarge.DEPLOYMENT_CFG, sarge.SUPERVISORD_CFG])
