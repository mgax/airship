from path import path
from mock import call
from common import SargeTestCase, imp


class WorkflowTest(SargeTestCase):

    def setUp(self):
        self.mock_supervisorctl = self.patch('sarge.daemons.Supervisor.ctl')
        self.instance = self.sarge().new_instance()

    def test_new_instance_creates_configuration_folder(self):
        self.instance.start()

        cfg_folder = path(self.instance.folder + '.cfg')
        self.assertTrue(cfg_folder.isdir())

        symlink_path = (self.tmp /
                        imp('sarge.core').CFG_LINKS_FOLDER /
                        self.instance.id_)
        self.assertTrue(symlink_path.islink())
        self.assertEqual(symlink_path.readlink(), cfg_folder)

    def test_new_instance_creates_runtime_folder(self):
        self.instance.start()

        run_folder = path(self.instance.folder + '.run')
        self.assertTrue(run_folder.isdir())

    def test_instance_start_triggers_supervisord_reread_and_restart(self):
        self.mock_supervisorctl.reset_mock()
        self.instance.start()
        self.assertIn(call(['update']),
                      self.mock_supervisorctl.mock_calls)
        self.assertIn(call(['restart', '%s:*' % self.instance.id_]),
                      self.mock_supervisorctl.mock_calls)

    def test_status_invokes_supervisorctl_status(self):
        self.mock_supervisorctl.reset_mock()
        self.sarge().status()
        self.assertIn(call(['status']), self.mock_supervisorctl.mock_calls)

    def test_enumerate_instances(self):
        self.assertEqual([d.name for d in self.sarge().deployments],
                         [self.instance.id_])
