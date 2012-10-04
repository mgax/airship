from common import SargeTestCase


def get_routes(haproxy_cfg):
    routes = {}
    for line in haproxy_cfg.splitlines():
        if ' bind ' in line:
            stable_port = int(line.split(':')[-1])
        if ' server ' in line and 'timeout' not in line:
            instance_port = int(line.split(':')[-1].split()[0])
            routes[stable_port] = instance_port
    return routes


class HaproxyConfigurationTest(SargeTestCase):

    def test_with_no_instances_we_have_empty_configuration_file(self):
        sarge = self.create_sarge()
        cfg = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg').text()
        self.assertIn('maxconn 256', cfg)
        self.assertIn('defaults', cfg)
        self.assertEqual(get_routes(cfg), {})

    def test_instance_with_stable_port_is_configured_in_haproxy(self):
        sarge = self.create_sarge({'port_map': {'testy': 8743}})
        instance = sarge.new_instance({'application_name': 'testy'})
        instance.start()
        cfg = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg').text()
        self.assertEqual(get_routes(cfg), {8743: instance.port})
