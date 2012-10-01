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
        self.nginx_tek().configure('zz.example.com:8080', {})
        self.assertEqual(collapse((self.tmp / 'zz.example.com:8080').text()),
                         'server { listen 8080; server_name zz.example.com; }')

    def test_nginx_configure_triggers_nginx_reload(self):
        self.nginx_tek().configure('zz.example.com:8080', {})
        self.assertEqual(self.reload_.mock_calls, [call()])

    def test_nginx_delete_removes_site(self):
        nginx = self.nginx_tek()
        nginx.configure('zz.example.com:8080', {})
        nginx.delete('zz.example.com:8080')
        self.assertEqual(self.tmp.listdir(), [])

    def test_nginx_delete_with_no_site_obeys_nofail_flag(self):
        self.nginx_tek().delete('zz.example.com:8080', nofail=True)

    def test_nginx_delete_triggers_nginx_reload(self):
        nginx = self.nginx_tek()
        nginx.configure('zz.example.com:8080', {})
        self.reload_.reset_mock()
        nginx.delete('zz.example.com:8080')
        self.assertEqual(self.reload_.mock_calls, [call()])

    def test_arbitrary_nginx_options_are_written_to_config(self):
        self.nginx_tek().configure('zz.example.com:80',
                                   {'options': {'send_timeout': '2m'}})
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()),
                         ('server { '
                            'listen 80; '
                            'send_timeout 2m; '
                            'server_name zz.example.com; '
                          '}'))

    def test_static_folder_is_configured_in_nginx(self):
        self.nginx_tek().configure('zz.example.com:80', {'urlmap': [
            {'url': '/media', 'type': 'static', 'path': '/var/local/x'}]})
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()),
                         ('server { '
                            'listen 80; '
                            'server_name zz.example.com; '
                            'location /media { '
                              'alias /var/local/x; '
                            '} '
                          '}'))

    def test_fcgi_route_is_configured_in_nginx(self):
        self.nginx_tek().configure('zz.example.com:80', {'urlmap': [
            {'url': '/app', 'type': 'fcgi', 'socket': 'localhost:24637'}]})
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()), (
            'server { '
              'listen 80; '
              'server_name zz.example.com; '
              'location /app { '
                'include /etc/nginx/fastcgi_params; '
                'fastcgi_param PATH_INFO $fastcgi_script_name; '
                'fastcgi_param SCRIPT_NAME ""; '
                'fastcgi_pass localhost:24637; '
              '} '
            '}'))

    def test_http_proxy_route_is_configured_in_nginx(self):
        self.nginx_tek().configure('zz.example.com:80', {'urlmap': [
            {'url': '/other', 'type': 'proxy',
             'upstream_url': 'http://backend:4912/some/path'}]})
        self.assertEqual(collapse((self.tmp / 'zz.example.com:80').text()), (
            'server { '
              'listen 80; '
              'server_name zz.example.com; '
              'location /other { '
                'proxy_pass http://backend:4912/some/path; '
                'proxy_redirect off; '
                'proxy_set_header X-Forwarded-Host $host; '
                'proxy_set_header X-Real-IP $remote_addr; '
                'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; '
              '} '
            '}'))

    def test_shell_configure_invocation_calls_configure_with_parameters(self):
        configure = self.patch('tek.nginx.NginxTek.configure')
        self.nginx_tek().main(['configure', 'zzz:8080', '{"a": "b"}'])
        self.assertEqual(configure.mock_calls,
                         [call(site_name='zzz:8080', config={'a': 'b'})])

    def test_shell_delete_invocation_calls_delete_with_parameters(self):
        delete = self.patch('tek.nginx.NginxTek.delete')
        self.nginx_tek().main(['delete', 'zzz:8080', '-f'])
        self.assertEqual(delete.mock_calls,
                         [call(site_name='zzz:8080', nofail=True)])
