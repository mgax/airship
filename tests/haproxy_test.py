from mock import patch, call
from common import SargeTestCase


def get_routes(haproxy_cfg):
    routes = {}
    for line in haproxy_cfg.splitlines():
        if ' bind ' in line:
            port_bind = line.strip().split()[-1]
        if ' server ' in line and 'timeout' not in line:
            bucket_port = int(line.split(':')[-1].split()[0])
            routes[port_bind] = bucket_port
    return routes


class HaproxyConfigurationTest(SargeTestCase):

    def test_with_no_buckets_we_have_empty_configuration_file(self):
        sarge = self.create_sarge()
        cfg = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg').text()
        self.assertIn('maxconn 256', cfg)
        self.assertIn('defaults', cfg)
        self.assertEqual(get_routes(cfg), {})

    def test_bucket_with_stable_port_is_configured_in_haproxy(self):
        sarge = self.create_sarge({'port_map': {'testy': '*:8743'}})
        bucket = sarge.new_bucket({'application_name': 'testy'})
        bucket.start()
        cfg = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg').text()
        self.assertEqual(get_routes(cfg), {'*:8743': bucket.port})

    def test_stopped_bucket_is_removed_from_haproxy(self):
        sarge = self.create_sarge({'port_map': {'testy': '*:8743'}})
        bucket = sarge.new_bucket({'application_name': 'testy'})
        bucket.start()
        cfg_file = (self.tmp / 'etc' / 'haproxy' / 'haproxy.cfg')
        self.assertEqual(get_routes(cfg_file.text()),
                                    {'*:8743': bucket.port})
        bucket.stop()
        self.assertEqual(get_routes(cfg_file.text()), {})

    def test_haproxy_reconfiguration_triggers_haproxy_restart(self):
        with patch('airship.daemons.Supervisor.ctl') as ctl:
            sarge = self.create_sarge({'port_map': {'testy': '*:8743'}})
            bucket = sarge.new_bucket({'application_name': 'testy'})
            bucket.start()
        self.assertIn(call(['restart', 'haproxy']), ctl.mock_calls)
