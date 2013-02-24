import os
from mock import Mock, patch, call, ANY
from common import AirshipTestCase


class PluginTest(AirshipTestCase):

    @patch('airship.core.pkg_resources')
    def test_plugin_function_called(self, pkg_resources):
        from airship.core import load_plugins
        entry_point = Mock()
        pkg_resources.iter_entry_points.return_value = [entry_point]
        airship = Mock()
        load_plugins(airship)
        self.assertEqual(entry_point.load.return_value.mock_calls,
                         [call(airship)])

    @patch('airship.deployer.subprocess')
    @patch('airship.deployer.bucket_setup')
    @patch('airship.deployer.remove_old_buckets')
    def test_deploy_sends_bucket_setup_signal(self, subprocess,
                                                    bucket_setup,
                                                    remove_old_buckets):
        from airship.deployer import deploy
        airship = Mock()
        bucket = airship.new_bucket.return_value
        deploy(airship, Mock())
        self.assertEqual(bucket_setup.send.mock_calls,
                         [call(airship, bucket=bucket)])

    @patch('airship.core.os')
    def test_run_sends_bucket_run_signal(self, mock_os):
        from airship.core import bucket_run
        mock_os.environ = os.environ
        airship = self.create_airship()
        bucket = airship.new_bucket()
        handler = Mock()
        with bucket_run.connected_to(handler):
            bucket.run('ls')
        self.assertEqual(handler.mock_calls,
                         [call(airship, bucket=bucket, environ=ANY)])
