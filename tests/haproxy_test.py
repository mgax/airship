from common import SargeTestCase


class HaproxyConfigurationTest(SargeTestCase):

    def test_with_no_instances_we_have_empty_configuration_file(self):
        sarge = self.create_sarge()
        haproxy_cfg = self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg'
        self.assertIn('maxconn 256', haproxy_cfg.text())
        self.assertIn('defaults', haproxy_cfg.text())
        self.assertNotIn('listen', haproxy_cfg.text())
