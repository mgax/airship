import re
from unittest import skip
from path import path
from common import SargeTestCase, imp


def read_config(cfg_path):
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


def create_sarge(home):
    return imp('sarge').Sarge({'home': home, 'plugins': ['sarge:NginxPlugin']})


class NginxConfigurationTest(SargeTestCase):

    def setUp(self):
        (self.tmp / 'etc' / 'nginx').makedirs()

    def configure_and_activate(self, deployment_config, sarge=None):
        if sarge is None:
            sarge = create_sarge(self.tmp)
        instance = sarge.new_instance(deployment_config)
        instance.configure()
        return instance

    def assert_equivalent(self, cfg1, cfg2):
        collapse = lambda s: re.sub('\s+', ' ', s).strip()
        self.assertEqual(collapse(cfg1), collapse(cfg2))

    def test_no_web_services_yields_blank_configuration(self):
        instance = self.configure_and_activate({})
        cfg_urlmap = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(cfg_urlmap, 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf, "")

    def test_static_folder_is_configured_in_nginx(self):
        instance = self.configure_and_activate({
            'urlmap': [
                {'url': '/media',
                 'type': 'static',
                 'path': 'mymedia'},
            ],
        })
        cfg_urlmap = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(cfg_urlmap, 'rb') as f:
            nginx_conf = f.read()
        conf_ok = ("location /media { alias %s/mymedia; }" %
                   instance.folder)
        self.assert_equivalent(nginx_conf, conf_ok)

    def test_php_app_is_configured_in_nginx(self):
        instance = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php'},
            ],
        })
        cfg_urlmap = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(cfg_urlmap, 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'location / { '
            '  include /etc/nginx/fastcgi_params; '
            '  fastcgi_param SCRIPT_FILENAME '
                          '%(instance.folder)s$fastcgi_script_name; '
            '  fastcgi_param PATH_INFO $fastcgi_script_name; '
            '  fastcgi_param SCRIPT_NAME ""; '
            '  fastcgi_pass unix:%(run_folder)s/php.sock; '
            '}' % {'instance.folder': instance.folder,
                   'run_folder': instance.run_folder})

    @skip('PHP setup broken when using instance api')
    def test_php_fcgi_startup_command_is_generated(self):
        instance = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php'},
            ],
        })
        cfg_folder = path(instance.folder + '.cfg')

        config_path = cfg_folder / imp('sarge.core').SUPERVISOR_DEPLOY_CFG
        command = read_config(config_path).get(
            'program:testy_fcgi_php', 'command')

        self.assertEqual(command, '/usr/bin/spawn-fcgi '
                                  '-s %(run_folder)s/php.sock -M 0777 '
                                  '-f /usr/bin/php5-cgi -n' % {
                                      'run_folder': instance.run_folder,
                                  })

    def test_proxy_is_configured_in_nginx(self):
        instance = self.configure_and_activate({
            'urlmap': [
                {'url': '/stuff',
                 'type': 'proxy',
                 'upstream_url': 'http://backend:4912/some/path'},
            ],
        })
        urlmap_path = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(urlmap_path, 'rb') as f:
            nginx_conf = f.read()
        conf_ok = (
            "location /stuff { "
            "proxy_pass http://backend:4912/some/path; "
            "proxy_redirect off; "
            "proxy_set_header Host $host; "
            "proxy_set_header X-Real-IP $remote_addr; "
            "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; "
            "}")
        self.assert_equivalent(nginx_conf, conf_ok)

    def test_process_with_hardcoded_tcp_socket_is_configured_in_nginx(self):
        instance = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'fcgi',
                 'socket': 'tcp://localhost:24637'},
            ],
        })
        urlmap_path = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(urlmap_path, 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'location / { '
            '  include /etc/nginx/fastcgi_params; '
            '  fastcgi_param PATH_INFO $fastcgi_script_name; '
            '  fastcgi_param SCRIPT_NAME ""; '
            '  fastcgi_pass localhost:24637; '
            '}')

    def test_process_with_hardcoded_unix_socket_is_configured_in_nginx(self):
        instance = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'fcgi',
                 'socket': 'unix:///path/to/socket'},
            ],
        })
        urlmap_path = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(urlmap_path, 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'location / { '
            '  include /etc/nginx/fastcgi_params; '
            '  fastcgi_param PATH_INFO $fastcgi_script_name; '
            '  fastcgi_param SCRIPT_NAME ""; '
            '  fastcgi_pass unix:/path/to/socket; '
            '}')

    @skip('Arbitrary nginx options are ignored when using instance api')
    def test_configure_nginx_arbitrary_options(self):
        instance = self.configure_and_activate({
            'nginx_options': {
                'server_name': 'something.example.com',
                'listen': '8013',
            },
        })
        cfg_site = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-site')
        with open(cfg_site, 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'server { '
            '    listen 8013; '
            '    server_name something.example.com; '
            '    include %(urlmap_path)s; '
            '}' % {'urlmap_path': cfg_site})

    def test_urlmap_value_is_interpolated_with_app_config_variable(self):
        from sarge import signals
        sarge = create_sarge(self.tmp)

        @signals.instance_configuring.connect_via(sarge, weak=True)
        def set_landcover(sarge, appcfg, **extra):
            appcfg['LANDCOVER'] = "Forest"

        instance = self.configure_and_activate({
            'urlmap': [{'url': '/media',
                        'type': 'static',
                        'path': 'mymedia/$LANDCOVER'}]}, sarge=sarge)
        cfg_urlmap = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        with open(cfg_urlmap, 'rb') as f:
            nginx_conf = f.read()
        conf_ok = ("location /media { alias %s/mymedia/Forest; }" %
                   instance.folder)
        self.assert_equivalent(nginx_conf, conf_ok)

    def test_nginx_configuration_is_removed_on_instance_destroy(self):
        instance = self.configure_and_activate({})
        cfg_urlmap = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-urlmap')
        cfg_site = self.tmp / 'etc' / 'nginx' / (instance.id_ + '-site')
        self.assertTrue(cfg_urlmap.isfile())
        self.assertTrue(cfg_site.isfile())
        instance.destroy()
        self.assertFalse(cfg_urlmap.isfile())
        self.assertFalse(cfg_site.isfile())
