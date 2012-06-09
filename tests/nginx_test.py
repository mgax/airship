import unittest
import tempfile
import json
import re
from path import path
from mock import patch


def read_config(cfg_path):
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


def setUpModule(self):
    global sarge
    import sarge


class NginxConfigurationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    def configure_and_activate(self, app_config):
        self.configure({'deployments': [{'name': 'testy'}]})
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

    def test_no_web_services_yields_blank_configuration(self):
        version_folder = self.configure_and_activate({})
        with open(version_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf, "")

    def test_static_folder_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/media',
                 'type': 'static',
                 'path': 'mymedia'},
            ],
        })
        with open(version_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "location /media { alias %s/mymedia; }" % version_folder)

    def test_wsgi_app_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'wsgi_app': 'wsgiref.simple_server:demo_app'},
            ],
        })
        with open(version_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "location / { "
            "    include /etc/nginx/fastcgi_params; "
            "    fastcgi_param PATH_INFO $fastcgi_script_name; "
            "    fastcgi_param SCRIPT_NAME ""; "
            "    fastcgi_pass unix:%(socket_path)s; "
            " }" % {'socket_path': version_folder/'wsgi-app.sock'})

    def test_php_app_is_configured_in_nginx(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php',
                 'path': '/myphpcode'},
            ],
        })
        with open(version_folder/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "location / { "
            "    include /etc/nginx/fastcgi_params; "
            "    fastcgi_param SCRIPT_FILENAME "
                            "%(version_folder)s$fastcgi_script_name; "
            "    fastcgi_param PATH_INFO $fastcgi_script_name; "
            "    fastcgi_param SCRIPT_NAME ""; "
            "    fastcgi_pass unix:%(version_folder)s/php.sock; "
            " }" % {'version_folder': version_folder})

    def test_php_fcgi_startup_command_is_generated(self):
        version_folder = self.configure_and_activate({
            'urlmap': [
                {'url': '/',
                 'type': 'php',
                 'path': '/myphpcode'},
            ],
        })

        config = read_config(self.tmp/sarge.SUPERVISORD_CFG)
        command = config.get('program:testy', 'command')

        self.assertEqual(command, "/usr/bin/spawn-fcgi "
                                  "-s %(version_folder)s/php.sock "
                                  "-f /usr/bin/php5-cgi -n" % {
                                      'version_folder': version_folder,
                                  })
