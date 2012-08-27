from path import path
from mock import call
from common import SargeTestCase, imp


class WorkflowTest(SargeTestCase):

    def setUp(self):
        self.mock_supervisorctl = self.patch('sarge.daemons.Supervisor.ctl')
        self.instance = self.sarge().new_instance()

    def test_new_instance_creates_runtime_folder(self):
        self.instance.start()
        self.assertTrue(self.instance.run_folder.isdir())

    def test_instance_start_triggers_supervisord_reread_and_restart(self):
        self.mock_supervisorctl.reset_mock()
        self.instance.start()
        self.assertIn(call(['update']),
                      self.mock_supervisorctl.mock_calls)
        self.assertIn(call(['restart', '%s:*' % self.instance.id_]),
                      self.mock_supervisorctl.mock_calls)

    def test_instance_stop_triggers_supervisord_stop(self):
        self.instance.start()
        self.mock_supervisorctl.reset_mock()
        self.instance.stop()
        self.assertIn(call(['stop', '%s:*' % self.instance.id_]),
                      self.mock_supervisorctl.mock_calls)
