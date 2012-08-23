from path import path
from mock import call
from common import configure_deployment, configure_sarge, imp
from common import SargeTestCase


class WorkflowTest(SargeTestCase):

    def setUp(self):
        self.mock_supervisorctl = self.patch('sarge.daemons.Supervisor.ctl')
        configure_sarge(self.tmp, {})
        configure_deployment(self.tmp, {'name': 'testy'})

    def test_new_version(self):
        testy = self.sarge().get_deployment('testy')
        version_folder = path(testy.new_version())
        self.assertTrue(version_folder.isdir())
        self.assertEqual(version_folder.parent.parent, self.tmp)

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

        symlink_path = self.tmp / imp('sarge.core').CFG_LINKS_FOLDER / 'testy'
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

        symlink_path = self.tmp / imp('sarge.core').CFG_LINKS_FOLDER / 'testy'
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
