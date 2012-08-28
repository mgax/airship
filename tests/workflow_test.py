from common import SargeTestCase


class WorkflowTest(SargeTestCase):

    def setUp(self):
        self.instance = self.sarge().new_instance()

    def test_new_instance_creates_runtime_folder(self):
        self.instance.start()
        self.assertTrue(self.instance.run_folder.isdir())

    def test_instance_stop_removes_run_folder(self):
        self.instance.start()
        run_folder = self.instance.run_folder
        self.assertTrue(run_folder.isdir())
        self.instance.stop()
        self.assertFalse(run_folder.isdir())

    def test_instance_destroy_removes_instance_folder_and_yaml(self):
        self.instance.start()
        instance_folder = self.instance.folder
        sarge = self.instance.sarge
        yaml_path = sarge._instance_config_path(self.instance.id_)
        self.assertTrue(instance_folder.isdir())
        self.assertTrue(yaml_path.isfile())
        self.instance.stop()
        self.instance.destroy()
        self.assertFalse(instance_folder.isdir())
        self.assertFalse(yaml_path.isfile())
