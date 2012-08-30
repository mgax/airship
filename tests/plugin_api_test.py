import json
from mock import Mock, call
from common import SargeTestCase, imp


mock_plugin = Mock()


class PluginApiTest(SargeTestCase):

    def sarge(self):
        return imp('sarge').Sarge({'home': self.tmp,
                                   'plugins': [__name__ + ':mock_plugin']})

    def test_plugin_named_in_config_file_gets_called(self):
        mock_plugin.reset_mock()
        s = self.sarge()
        self.assertEqual(mock_plugin.mock_calls, [call(s)])

    def test_subscribe_to_activation_event(self):
        mock_handler = Mock(im_self=None)
        sarge = self.sarge()
        self.signal('instance-will-start').connect(mock_handler, sarge)
        sarge.new_instance().start()
        self.assertEqual(len(mock_handler.mock_calls), 1)

    def test_value_injected_via_configure_event_is_available_to_app(self):
        from sarge import signals
        sarge = self.sarge()

        @signals.instance_configuring.connect_via(sarge, weak=True)
        def handler(sarge, instance, appcfg, **extra):
            appcfg['your-order'] = "is here"

        instance = sarge.new_instance()
        instance.configure()

        with instance.appcfg_path.open() as f:
            appcfg = json.load(f)
        self.assertEqual(appcfg['your-order'], "is here")

    def test_instance_stop_triggers_stop_signal(self):
        from sarge import signals
        stopped = []
        sarge = self.sarge()

        @signals.instance_has_stopped.connect_via(sarge, weak=True)
        def handler(sarge, instance, **extra):
            stopped.append(instance.id_)

        instance = sarge.new_instance()
        instance.start()
        instance.stop()
        self.assertEqual(stopped, [instance.id_])

    def test_instance_destroy_triggers_destroy_signal(self):
        from sarge import signals
        destroyed = []
        sarge = self.sarge()

        @signals.instance_will_be_destroyed.connect_via(sarge, weak=True)
        def handler(sarge, instance, **extra):
            destroyed.append(instance.id_)

        instance = sarge.new_instance()
        instance.start()
        instance.stop()
        instance.destroy()
        self.assertEqual(destroyed, [instance.id_])
