from utils import unittest
import tempfile
import json
from path import path
from mock import Mock, patch, call
from utils import configure_sarge, configure_deployment, username


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


mock_plugin = Mock()


class PluginApiTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def test_plugin_named_in_config_file_gets_called(self):
        configure_sarge(self.tmp, {'plugins': [__name__+':mock_plugin']})
        mock_plugin.reset_mock()
        s = sarge.Sarge(self.tmp)
        self.assertEqual(mock_plugin.mock_calls, [call(s)])

    def test_subscribe_to_activation_event(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        mock_handler = Mock(im_self=None)
        s.on_activate_version.connect(mock_handler)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)
        self.assertEqual(mock_handler.mock_calls,
                         [call(testy, folder=version_folder)])
