from common import AirshipTestCase


class WorkflowTest(AirshipTestCase):

    def setUp(self):
        self.bucket = self.create_airship().new_bucket()

    def test_new_bucket_creates_runtime_folder(self):
        self.bucket.start()
        self.assertTrue(self.bucket.run_folder.isdir())

    def test_bucket_destroy_removes_bucket_folder_and_run(self):
        self.bucket.start()
        bucket_folder = self.bucket.folder
        airship = self.bucket.airship
        run_folder = self.bucket.run_folder

        self.assertTrue(bucket_folder.isdir())
        self.assertTrue(run_folder.isdir())

        self.bucket.stop()
        self.bucket.destroy()
        self.assertFalse(bucket_folder.isdir())
        self.assertFalse(run_folder.isdir())

    def test_destroy_does_not_fail_if_called_twice(self):
        self.bucket.start()
        self.bucket.stop()
        self.bucket.destroy()
        self.bucket.destroy()
