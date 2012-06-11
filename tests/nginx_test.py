import unittest
import tempfile
import json
import re
from path import path
from mock import patch, call


def read_config(cfg_path):
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


def setUpModule(self):
    global sarge, _subprocess_patch, mock_subprocess
    import sarge
    _subprocess_patch = patch('sarge.subprocess')
    mock_subprocess = _subprocess_patch.start()


def tearDownModule(self):
    _subprocess_patch.stop()


class NginxConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    def configure_and_activate(self, app_config):
        self.configure({
            'plugins': ['sarge:NginxPlugin'],
            'deployments': [{'name': 'testy'}],
        })
        s = sarge.Sarge(self.tmp)
        deployment = s.get_deployment('testy')
        version_folder = path(deployment.new_version())
        with open(version_folder/'sargeapp.yaml', 'wb') as f:
            json.dump(app_config, f)
        deployment.activate_version(version_folder)
        run_folder = path(version_folder + '.run')
        return version_folder, run_folder

    def assert_equivalent(self, cfg1, cfg2):
        collapse = lambda s: re.sub('\s+', ' ', s).strip()
        self.assertEqual(collapse(cfg1), collapse(cfg2))

    def test_no_web_services_yields_blank_configuration(self):
        version_folder, run_folder = self.configure_and_activate({})
        with open(run_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf, "server { }")

    def test_static_folder_is_configured_in_nginx(self):
        version_folder, run_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/media',
                 'type': 'static',
                 'path': 'mymedia'},
            ],
        })
        with open(run_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "server { location /media { alias %s/mymedia; } }" % version_folder)

    def test_wsgi_app_is_configured_in_nginx(self):
        version_folder, run_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'wsgi_app': 'wsgiref.simple_server:demo_app'},
            ],
        })
        with open(run_folder/'nginx-site.conf', 'rb') as f:
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
        version_folder, run_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php',
                 'path': '/myphpcode'},
            ],
        })
        with open(run_folder/'nginx-site.conf', 'rb') as f:
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
        version_folder, run_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php',
                 'path': '/myphpcode'},
            ],
        })

        config_path = run_folder/sarge.SUPERVISOR_DEPLOY_CFG
        command = read_config(config_path).get('program:testy', 'command')

        self.assertEqual(command, '/usr/bin/spawn-fcgi '
                                  '-s %(run_folder)s/php.sock '
                                  '-f /usr/bin/php5-cgi -n' % {
                                      'run_folder': run_folder,
                                  })

    def test_configure_nginx_arbitrary_options(self):
        version_folder, run_folder = self.configure_and_activate({
            'nginx_options': {
                'server_name': 'something.example.com',
                'listen': '8013',
            },
        })
        with open(run_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            'server { '
            '    listen 8013; '
            '    server_name something.example.com; '
            '}')

    def test_activate_triggers_nginx_service_reload(self):
        mock_subprocess.reset_mock()
        version_folder, run_folder = self.configure_and_activate({})
        self.assertIn(call(['service', 'nginx', 'reload']),
                      mock_subprocess.check_call.mock_calls)
