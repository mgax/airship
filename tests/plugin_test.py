from mock import Mock, patch, call
from common import AirshipTestCase


class PluginTest(AirshipTestCase):

    @patch('airship.core.pkg_resources')
    def test_plugin_function_called(self, pkg_resources):
        from airship.core import load_plugins
        entry_point = Mock()
        pkg_resources.iter_entry_points.return_value = [entry_point]
        load_plugins()
        self.assertEqual(entry_point.load.return_value.mock_calls, [call()])

    @patch('airship.deployer.subprocess')
    @patch('airship.deployer.bucket_setup')
    @patch('airship.deployer.remove_old_buckets')
    def test_deploy_sends_bucket_setup_signal(self, subprocess,
                                                    bucket_setup,
                                                    remove_old_buckets):
        from airship.deployer import deploy
        sarge = Mock()
        bucket = sarge.new_bucket.return_value
        deploy(sarge, Mock(), 'web')
        self.assertEqual(bucket_setup.send.mock_calls, [call(bucket)])
