import re
from mock import call
from common import HandyTestCase


def collapse(s):
    return re.sub('\s+', ' ', s).strip()


class TekNginxTest(HandyTestCase):

    def setUp(self):
        self.reload_ = self.patch('tek.nginx.NginxTek.reload_')

    def nginx_tek(self):
        from tek.nginx import NginxTek
        return NginxTek(sites_dir=self.tmp)

    def test_nginx_configure_with_empty_urlmap_creates_blank_site(self):
        self.nginx_tek().configure('zz.example.com', 8080)
        self.assertEqual(collapse((self.tmp / 'zz.example.com:8080').text()),
                         'server { server_name zz.example.com; listen 8080; }')

    def test_nginx_configure_triggers_nginx_reload(self):
        self.nginx_tek().configure('zz.example.com', 8080)
        self.assertEqual(self.reload_.mock_calls, [call()])

    def test_nginx_delete_removes_site(self):
        nginx = self.nginx_tek()
        nginx.configure('zz.example.com', 8080)
        nginx.delete('zz.example.com', 8080)
        self.assertEqual(self.tmp.listdir(), [])

    def test_nginx_delete_triggers_nginx_reload(self):
        nginx = self.nginx_tek()
        nginx.configure('zz.example.com', 8080)
        self.reload_.reset_mock()
        nginx.delete('zz.example.com', 8080)
        self.assertEqual(self.reload_.mock_calls, [call()])
