import unittest
import tempfile
import json
from path import path
from mock import Mock, patch, call


def setUpModule(self):
    global sarge, _subprocess_patch, mock_subprocess
    import sarge
    _subprocess_patch = patch('sarge.subprocess')
    mock_subprocess = _subprocess_patch.start()


def tearDownModule(self):
    _subprocess_patch.stop()


mock_plugin = Mock()


class PluginApiTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    def test_plugin_named_in_config_file_gets_called(self):
        self.configure({
            'plugins': [__name__+':mock_plugin'],
            'deployments': [],
        })
        mock_plugin.reset_mock()
        s = sarge.Sarge(self.tmp)
        self.assertEqual(mock_plugin.mock_calls, [call(s)])

    def test_subscribe_to_activation_event(self):
        self.configure({'deployments': [{'name': 'testy'}]})
        s = sarge.Sarge(self.tmp)
        mock_handler = Mock(im_self=None)
        s.on_activate_version.connect(mock_handler)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)
        self.assertEqual(mock_handler.mock_calls,
                         [call(testy, folder=version_folder)])
