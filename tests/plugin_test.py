from mock import Mock, patch, call
from common import SargeTestCase


class PluginTest(SargeTestCase):

    @patch('sarge.core.pkg_resources')
    def test_plugin_function_called(self, pkg_resources):
        from sarge.core import load_plugins
        callback = Mock()
        pkg_resources.iter_entry_points.return_value = [callback]
        load_plugins()
        self.assertEqual(callback.mock_calls, [call()])

    @patch('sarge.deployer.subprocess')
    def test_deploy_sends_bucket_setup_signal(self, subprocess):
        from sarge.deployer import set_up_bucket, bucket_setup
        bucket = Mock()
        bucket.meta = {'APPLICATION_NAME': 'web'}
        bucket_folder = bucket.folder = self.tmp / 'the-bucket'
        bucket_folder.mkdir()
        (bucket_folder / 'Procfile').write_text('web: sleep 5\n')
        callback = Mock()
        bucket_setup.connect(callback.__call__)
        set_up_bucket(bucket)
        self.assertEqual(callback.mock_calls, [call(bucket)])
