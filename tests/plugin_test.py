from mock import Mock, patch, call
from common import SargeTestCase


class PluginTest(SargeTestCase):

    @patch('sarge.core.pkg_resources')
    def test_plugin_function_called(self, pkg_resources):
        from sarge.core import load_plugins
        entry_point = Mock()
        pkg_resources.iter_entry_points.return_value = [entry_point]
        load_plugins()
        self.assertEqual(entry_point.load.return_value.mock_calls, [call()])

    @patch('sarge.deployer.subprocess')
    @patch('sarge.deployer.bucket_setup')
    @patch('sarge.deployer.remove_old_buckets')
    def test_deploy_sends_bucket_setup_signal(self, subprocess,
                                                    bucket_setup,
                                                    remove_old_buckets):
        from sarge.deployer import deploy
        sarge = Mock()
        bucket = sarge.new_bucket.return_value
        deploy(sarge, Mock(), 'web')
        self.assertEqual(bucket_setup.send.mock_calls, [call(bucket)])
