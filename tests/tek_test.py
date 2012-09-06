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
        return NginxTek(sites_dir=str(self.tmp))

    def test_nginx_configure_with_empty_urlmap_creates_blank_site(self):
        self.nginx_tek().configure('zz.example.com', 8080, [])
        self.assertEqual(collapse((self.tmp / 'zz.example.com:8080').text()),
                         'server { server_name zz.example.com; listen 8080; }')

    def test_nginx_configure_triggers_nginx_reload(self):
        self.nginx_tek().configure('zz.example.com', 8080, [])
        self.assertEqual(self.reload_.mock_calls, [call()])

    def test_nginx_delete_removes_site(self):
        nginx = self.nginx_tek()
        nginx.configure('zz.example.com', 8080, [])
        nginx.delete('zz.example.com', 8080)
        self.assertEqual(self.tmp.listdir(), [])

    def test_nginx_delete_triggers_nginx_reload(self):
        nginx = self.nginx_tek()
        nginx.configure('zz.example.com', 8080, [])
        self.reload_.reset_mock()
        nginx.delete('zz.example.com', 8080)
        self.assertEqual(self.reload_.mock_calls, [call()])

    def test_static_folder_is_configured_in_nginx(self):
        self.nginx_tek().configure('zz.example.com', 80, urlmap=[
            {'url': '/media', 'type': 'static', 'path': '/var/local/x'}])
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()),
                         ('server { '
                            'server_name zz.example.com; '
                            'listen 80; '
                            'location /media { '
                              'alias /var/local/x; '
                            '} '
                          '}'))

    def test_fcgi_route_is_configured_in_nginx(self):
        self.nginx_tek().configure('zz.example.com', 80, urlmap=[
            {'url': '/app', 'type': 'fcgi', 'socket': 'localhost:24637'}])
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()), (
            'server { '
              'server_name zz.example.com; '
              'listen 80; '
              'location /app { '
                'include /etc/nginx/fastcgi_params; '
                'fastcgi_param PATH_INFO $fastcgi_script_name; '
                'fastcgi_param SCRIPT_NAME ""; '
                'fastcgi_pass localhost:24637; '
              '} '
            '}'))

    def test_http_proxy_route_is_configured_in_nginx(self):
        self.nginx_tek().configure('zz.example.com', 80, urlmap=[
            {'url': '/other', 'type': 'proxy',
             'upstream_url': 'http://backend:4912/some/path'}])
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()), (
            'server { '
              'server_name zz.example.com; '
              'listen 80; '
              'location /other { '
                'proxy_pass http://backend:4912/some/path; '
                'proxy_redirect off; '
                'proxy_set_header Host $host; '
                'proxy_set_header X-Real-IP $remote_addr; '
                'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; '
              '} '
            '}'))
