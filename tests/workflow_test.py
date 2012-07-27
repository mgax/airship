import tempfile
from StringIO import StringIO
from path import path
from mock import patch, call
from common import configure_deployment, configure_sarge, username, imp
from common import SargeTestCase


class WorkflowTest(SargeTestCase):

    def setUp(self):
        self.mock_supervisorctl = self.patch('sarge.Sarge.supervisorctl')
        configure_sarge(self.tmp, {})
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})

    def test_new_version(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        self.assertTrue(version_folder.isdir())
        self.assertEqual(version_folder.parent.parent, self.tmp)

    def test_new_version_with_user_option_calls_chown(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': 'someone'})
        testy = self.sarge().get_deployment('testy')
        self.mock_subprocess.reset_mock()
        version_folder = path(testy.new_version())
        self.assertIn(call(['chown', 'someone:', version_folder]),
                      self.mock_subprocess.mock_calls)

    def test_activation_with_user_option_calls_chown(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': 'someone'})
        testy = self.sarge().get_deployment('testy')
        self.mock_subprocess.reset_mock()
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)
        run_folder = path(version_folder + '.run')
        self.assertIn(call(['chown', 'someone:', run_folder]),
                      self.mock_subprocess.mock_calls)

    def test_versions_have_different_paths(self):
        testy = self.sarge().get_deployment('testy')
        version_path_1 = path(testy.new_version())
        version_path_2 = path(testy.new_version())
        self.assertNotEqual(version_path_1, version_path_2)

    def test_activation_creates_configuration_folder(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        cfg_folder = path(version_folder + '.cfg')
        self.assertTrue(cfg_folder.isdir())

        symlink_path = self.tmp / imp('sarge').CFG_LINKS_FOLDER / 'testy'
        self.assertTrue(symlink_path.islink())
        self.assertEqual(symlink_path.readlink(), cfg_folder)

    def test_activation_creates_runtime_folder(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        run_folder = path(version_folder + '.run')
        self.assertTrue(run_folder.isdir())

    def test_activation_next_version_overwrites_symlink(self):
        testy = self.sarge().get_deployment('testy')
        version_folder_1 = path(testy.new_version())
        testy.activate_version(version_folder_1)
        version_folder_2 = path(testy.new_version())
        testy.activate_version(version_folder_2)

        cfg_folder_2 = path(version_folder_2 + '.cfg')
        self.assertTrue(cfg_folder_2.isdir())

        symlink_path = self.tmp / imp('sarge').CFG_LINKS_FOLDER / 'testy'
        self.assertTrue(symlink_path.islink())
        self.assertEqual(symlink_path.readlink(), cfg_folder_2)

    def test_activation_triggers_supervisord_reread(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())

        self.mock_supervisorctl.reset_mock()
        testy.activate_version(version_folder)
        self.assertIn(call(['update']), self.mock_supervisorctl.mock_calls)

    def test_activation_triggers_supervisord_restart_deployment(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())

        self.mock_supervisorctl.reset_mock()
        testy.activate_version(version_folder)
        self.assertIn(call(['restart', 'testy:*']),
                      self.mock_supervisorctl.mock_calls)

    def test_start_deployment_invokes_supervisorctl_start(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        self.mock_supervisorctl.reset_mock()
        testy.start()
        self.assertIn(call(['start', 'testy:*']),
                      self.mock_supervisorctl.mock_calls)

    def test_stop_deployment_invokes_supervisorctl_stop(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        testy.activate_version(version_folder)

        self.mock_supervisorctl.reset_mock()
        testy.stop()
        self.assertIn(call(['stop', 'testy:*']),
                      self.mock_supervisorctl.mock_calls)

    def test_status_invokes_supervisorctl_status(self):
        self.mock_supervisorctl.reset_mock()
        self.sarge().status()
        self.assertIn(call(['status']), self.mock_supervisorctl.mock_calls)


class ShellTest(SargeTestCase):

    def setUp(self):
        configure_sarge(self.tmp, {})

    @patch('sarge.Deployment.new_version')
    def test_new_version_calls_api_method(self, mock_new_version):
        mock_new_version.return_value = "path-to-new-version"
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        mock_stdout = StringIO()
        with patch('sys.stdout', mock_stdout):
            imp('sarge').main([str(self.tmp), 'new_version', 'testy'])
        self.assertEqual(mock_new_version.mock_calls, [call()])
        self.assertEqual(mock_stdout.getvalue().strip(), "path-to-new-version")

    @patch('sarge.Deployment.activate_version')
    def test_activate_version_calls_api_method(self, mock_activate_version):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        imp('sarge').main([str(self.tmp), 'activate_version',
                    'testy', str(version_folder)])
        self.assertEqual(mock_activate_version.mock_calls,
                         [call(version_folder)])
        path_arg = mock_activate_version.mock_calls[0][1][0]
        self.assertIsInstance(path_arg, path)

    @patch('sarge.Deployment.start')
    def test_start_calls_api_method(self, mock_start):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        imp('sarge').main([str(self.tmp), 'start', 'testy'])
        self.assertEqual(mock_start.mock_calls, [call()])

    @patch('sarge.Deployment.stop')
    def test_stop_calls_api_method(self, mock_stop):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        imp('sarge').main([str(self.tmp), 'stop', 'testy'])
        self.assertEqual(mock_stop.mock_calls, [call()])

    @patch('sarge.Sarge.status')
    def test_status_calls_api_method(self, mock_status):
        imp('sarge').main([str(self.tmp), 'status'])
        self.assertEqual(mock_status.mock_calls, [call()])

    def test_init_creates_configuration(self):
        other_tmp = path(tempfile.mkdtemp())
        self.addCleanup(other_tmp.rmtree)
        configure_sarge(other_tmp, {})

        sarge = imp('sarge')
        sarge.main([str(other_tmp), 'init'])
        expected = [sarge.SUPERVISORD_CFG,
                    sarge.DEPLOYMENT_CFG_DIR,
                    sarge.SARGE_CFG,
                    'sarge.log']
        self.assertItemsEqual([f.name for f in other_tmp.listdir()], expected)
        self.assertTrue((other_tmp / sarge.DEPLOYMENT_CFG_DIR).isdir())
