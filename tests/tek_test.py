import re
from common import HandyTestCase


def collapse(s):
    return re.sub('\s+', ' ', s).strip()


class TekNginxTest(HandyTestCase):

    def test_nginx_configure_with_empty_urlmap_creates_blank_site(self):
        from tek.nginx import NginxTek
        nginx = NginxTek(sites_dir=self.tmp)
        nginx.configure('zz.example.com')
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()),
                         'server { server_name zz.example.com; listen 80; }')
