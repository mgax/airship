import tempfile
from StringIO import StringIO
import json
from path import path
from mock import Mock, patch, call
from common import SargeTestCase, configure_deployment, imp


class ShellTest(SargeTestCase):

    def setUp(self):
        (self.tmp / imp('sarge.core').SARGE_CFG).write_text('{}')

    @patch('sarge.core.Sarge.new_instance')
    def test_new_instance_calls_api_and_returns_path(self, new_instance):
        new_instance.return_value = Mock(folder="path-to-new-version")
        with patch('sys.stdout', StringIO()) as stdout:
            imp('sarge.core').main([str(self.tmp), 'new_instance'])
        self.assertEqual(new_instance.mock_calls, [call()])
        self.assertEqual(stdout.getvalue().strip(), "path-to-new-version")

    @patch('sarge.core.Deployment.new_version')
    def test_new_version_calls_api_method(self, mock_new_version):
        mock_new_version.return_value = "path-to-new-version"
        configure_deployment(self.tmp, {'name': 'testy'})
        mock_stdout = StringIO()
        with patch('sys.stdout', mock_stdout):
            imp('sarge.core').main([str(self.tmp), 'new_version', 'testy'])
        self.assertEqual(mock_new_version.mock_calls, [call()])
        self.assertEqual(mock_stdout.getvalue().strip(), "path-to-new-version")

    @patch('sarge.core.Deployment.activate_version')
    def test_activate_version_calls_api_method(self, mock_activate_version):
        configure_deployment(self.tmp, {'name': 'testy'})
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        imp('sarge.core').main([str(self.tmp), 'activate_version',
                    'testy', str(version_folder)])
        self.assertEqual(mock_activate_version.mock_calls,
                         [call(version_folder)])
        path_arg = mock_activate_version.mock_calls[0][1][0]
        self.assertIsInstance(path_arg, path)

    @patch('sarge.core.Deployment.start')
    def test_start_calls_api_method(self, mock_start):
        configure_deployment(self.tmp, {'name': 'testy'})
        imp('sarge.core').main([str(self.tmp), 'start', 'testy'])
        self.assertEqual(mock_start.mock_calls, [call()])

    @patch('sarge.core.Deployment.stop')
    def test_stop_calls_api_method(self, mock_stop):
        configure_deployment(self.tmp, {'name': 'testy'})
        imp('sarge.core').main([str(self.tmp), 'stop', 'testy'])
        self.assertEqual(mock_stop.mock_calls, [call()])

    @patch('sarge.Sarge.status')
    def test_status_calls_api_method(self, mock_status):
        imp('sarge.core').main([str(self.tmp), 'status'])
        self.assertEqual(mock_status.mock_calls, [call()])

    @patch('sarge.core.status_cmd')
    def test_shell_invocation_loads_sarge_configuration(self, status_cmd):
        with open(self.tmp / imp('sarge.core').SARGE_CFG, 'wb') as f:
            json.dump({'hello': 'world'}, f)
        imp('sarge.core').main([str(self.tmp), 'status'])
        sarge = status_cmd.mock_calls[0][1][0]
        self.assertEqual(sarge.config['hello'], 'world')

    def test_init_creates_configuration(self):
        other_tmp = path(tempfile.mkdtemp())
        self.addCleanup(other_tmp.rmtree)
        (other_tmp / imp('sarge.core').SARGE_CFG).write_text('{}')

        core = imp('sarge.core')
        core.main([str(other_tmp), 'init'])
        expected = [core.SUPERVISORD_CFG,
                    core.DEPLOYMENT_CFG_DIR,
                    core.SARGE_CFG,
                    'sarge.log']
        self.assertItemsEqual([f.name for f in other_tmp.listdir()], expected)
        self.assertTrue((other_tmp / core.DEPLOYMENT_CFG_DIR).isdir())
