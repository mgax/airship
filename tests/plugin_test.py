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
