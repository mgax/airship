from common import SargeTestCase


class WorkflowTest(SargeTestCase):

    def setUp(self):
        self.bucket = self.create_sarge().new_bucket()

    def test_new_bucket_creates_runtime_folder(self):
        self.bucket.start()
        self.assertTrue(self.bucket.run_folder.isdir())

    def test_bucket_destroy_removes_bucket_folder_and_run_and_yaml(self):
        self.bucket.start()
        bucket_folder = self.bucket.folder
        sarge = self.bucket.sarge
        yaml_path = sarge._bucket_config_path(self.bucket.id_)
        run_folder = self.bucket.run_folder

        self.assertTrue(bucket_folder.isdir())
        self.assertTrue(yaml_path.isfile())
        self.assertTrue(run_folder.isdir())

        self.bucket.stop()
        self.bucket.destroy()
        self.assertFalse(bucket_folder.isdir())
        self.assertFalse(yaml_path.isfile())
        self.assertFalse(run_folder.isdir())

    def test_destroy_does_not_fail_if_called_twice(self):
        self.bucket.start()
        self.bucket.stop()
        self.bucket.destroy()
        self.bucket.destroy()
