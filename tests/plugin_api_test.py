import json
from path import path
from mock import Mock, patch, call
from common import configure_sarge, configure_deployment, username
from common import SargeTestCase


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


mock_plugin = Mock()


class PluginApiTest(SargeTestCase):

    def setUp(self):
        configure_sarge(self.tmp, {})

    def test_plugin_named_in_config_file_gets_called(self):
        configure_sarge(self.tmp, {'plugins': [__name__+':mock_plugin']})
        mock_plugin.reset_mock()
        s = self.sarge()
        self.assertEqual(mock_plugin.mock_calls, [call(s)])

    def test_subscribe_to_activation_event(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = self.sarge()
        mock_handler = Mock(im_self=None)
        s.on_activate_version.connect(mock_handler)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)
        self.assertEqual(len(mock_handler.mock_calls), 1)

    def test_activation_event_passes_shared_dict(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = self.sarge()

        def handler1(depl, share, **extra):
            share['test-something'] = 123

        got = []
        def handler2(depl, share, **extra):
            got.append(share.get('test-something'))

        s.on_activate_version.connect(handler1)
        s.on_activate_version.connect(handler2)

        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)
        self.assertEqual(got, [123])

    def test_activation_event_allows_passing_info_to_application(self):
        def handler(depl, appcfg, **extra):
            appcfg['your-order'] = "is here"

        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = self.sarge()
        s.on_activate_version.connect(handler)

        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        cfg_folder = path(version_folder + '.cfg')
        testy.activate_version(version_folder)

        with (cfg_folder/sarge.APP_CFG).open() as f:
            appcfg = json.load(f)
        self.assertEqual(appcfg['your-order'], "is here")
