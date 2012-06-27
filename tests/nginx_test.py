from utils import unittest
import tempfile
import json
import re
from path import path
from mock import patch, call
from utils import configure_sarge, configure_deployment, username


def read_config(cfg_path):
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


class NginxConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        configure_sarge(self.tmp, {'plugins': ['sarge:NginxPlugin']})

    def configure_and_activate(self, app_config, deployment_config_extra={}):
        deployment_config = {'name': 'testy', 'user': username}
        deployment_config.update(deployment_config_extra)
        configure_deployment(self.tmp, deployment_config)
        s = sarge.Sarge(self.tmp)
        deployment = s.get_deployment('testy')
        version_folder = path(deployment.new_version())
        with open(version_folder/'sargeapp.yaml', 'wb') as f:
            json.dump(app_config, f)
        deployment.activate_version(version_folder)
        return version_folder

    def assert_equivalent(self, cfg1, cfg2):
        collapse = lambda s: re.sub('\s+', ' ', s).strip()
        self.assertEqual(collapse(cfg1), collapse(cfg2))

    def test_nginx_common_config_created_on_init(self):
        sarge.init_cmd(sarge.Sarge(self.tmp), None)
        nginx_folder = self.tmp/sarge.NginxPlugin.FOLDER_NAME
        nginx_sites = nginx_folder/'sites'
        self.assertTrue(nginx_sites.isdir())

        nginx_common = nginx_folder/'sarge_sites.conf'
        self.assertTrue(nginx_common.isfile())
        self.assertEqual(nginx_common.text(),
                         'include ' + nginx_folder + '/sites/*;\n')

    def test_no_web_services_yields_blank_configuration(self):
        version_folder = self.configure_and_activate({})
        cfg_folder = path(version_folder + '.cfg')
        with open(cfg_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf, "server { }")

    def test_activation_creates_symlink_in_sites_folder(self):
        version_folder = self.configure_and_activate({})
        cfg_folder = path(version_folder + '.cfg')
        nginx_folder = self.tmp/sarge.NginxPlugin.FOLDER_NAME
        link_path = nginx_folder/'sites'/'testy'
        link_target = cfg_folder/'nginx-site.conf'
        self.assertTrue(link_path.islink())
        self.assertEqual(link_path.readlink(), link_target)

    def test_static_folder_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/media',
                 'type': 'static',
                 'path': 'mymedia'},
            ],
        })
        cfg_folder = path(version_folder + '.cfg')
        with open(cfg_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "server { location /media { alias %s/mymedia; } }" % version_folder)

    def test_wsgi_app_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'app_factory': 'wsgiref.simple_server:demo_app'},
            ],
        })
        cfg_folder = path(version_folder + '.cfg')
        run_folder = path(version_folder + '.run')
        with open(cfg_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'server { '
            '  location / { '
            '    include /etc/nginx/fastcgi_params; '
            '    fastcgi_param PATH_INFO $fastcgi_script_name; '
            '    fastcgi_param SCRIPT_NAME ""; '
            '    fastcgi_pass unix:%(socket_path)s; '
            '  } '
            '}' % {'socket_path': run_folder/'wsgi-app.sock'})

    def test_php_app_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php'},
            ],
        })
        cfg_folder = path(version_folder + '.cfg')
        run_folder = path(version_folder + '.run')
        with open(cfg_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'server { '
            '  location / { '
            '    include /etc/nginx/fastcgi_params; '
            '    fastcgi_param SCRIPT_FILENAME '
                            '%(version_folder)s$fastcgi_script_name; '
            '    fastcgi_param PATH_INFO $fastcgi_script_name; '
            '    fastcgi_param SCRIPT_NAME ""; '
            '    fastcgi_pass unix:%(run_folder)s/php.sock; '
            '  } '
            '}' % {'version_folder': version_folder,
                   'run_folder': run_folder})

    def test_php_fcgi_startup_command_is_generated(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php'},
            ],
        })
        cfg_folder = path(version_folder + '.cfg')
        run_folder = path(version_folder + '.run')
        cfg_folder = path(version_folder + '.cfg')

        config_path = cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG
        command = read_config(config_path).get(
            'program:testy_fcgi_php', 'command')

        self.assertEqual(command, '/usr/bin/spawn-fcgi '
                                  '-s %(run_folder)s/php.sock -M 0777 '
                                  '-f /usr/bin/php5-cgi -n' % {
                                      'run_folder': run_folder,
                                  })

    def test_process_with_hardcoded_tcp_socket_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'fcgi',
                 'socket': 'tcp://localhost:24637'},
            ],
        })
        cfg_folder = path(version_folder + '.cfg')
        with open(cfg_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'server { '
            '  location / { '
            '    include /etc/nginx/fastcgi_params; '
            '    fastcgi_param PATH_INFO $fastcgi_script_name; '
            '    fastcgi_param SCRIPT_NAME ""; '
            '    fastcgi_pass localhost:24637; '
            '  } '
            '}' % {'version_folder': version_folder})

    def test_configure_nginx_arbitrary_options(self):
        version_folder = self.configure_and_activate({}, {
            'nginx_options': {
                'server_name': 'something.example.com',
                'listen': '8013',
            },
        })
        cfg_folder = path(version_folder + '.cfg')
        with open(cfg_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'server { '
            '    listen 8013; '
            '    server_name something.example.com; '
            '}')

    def test_activate_triggers_nginx_service_reload(self):
        mock_subprocess.reset_mock()
        version_folder = self.configure_and_activate({})
        self.assertIn(call(['service', 'nginx', 'reload']),
                      mock_subprocess.check_call.mock_calls)
