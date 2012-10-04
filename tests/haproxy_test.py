from common import SargeTestCase


class HaproxyConfigurationTest(SargeTestCase):

    def test_with_no_instances_we_have_empty_configuration_file(self):
        sarge = self.create_sarge()
        cfg = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg').text()
        self.assertIn('maxconn 256', cfg)
        self.assertIn('defaults', cfg)
        self.assertNotIn('listen', cfg)

    def test_instance_with_stable_port_is_configured_in_haproxy(self):
        sarge = self.create_sarge({'port_map': {'testy': 8743}})
        instance = sarge.new_instance({'application_name': 'testy'})
        instance.start()
        cfg = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg').text()
        self.assertIn('listen testy', cfg)
        self.assertIn(' bind *:8743', cfg)
        self.assertIn(' server testy1 127.0.0.1:%d' % instance.port, cfg)
