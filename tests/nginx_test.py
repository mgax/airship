import unittest
import tempfile
import json
import re
from path import path
from mock import patch


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

    def configure_and_activate(self, deployment_config):
        self.configure({'deployments': [deployment_config]})
        s = sarge.Sarge(self.tmp)
        deployment = s.get_deployment(deployment_config['name'])
        version_path = path(deployment.new_version())
        deployment.activate_version(version_path)
        return version_path

    def assert_equivalent(self, cfg1, cfg2):
        collapse = lambda s: re.sub('\s+', ' ', s).strip()
        self.assertEqual(collapse(cfg1), collapse(cfg2))

    def test_no_web_services_yields_blank_configuration(self):
        version_path = self.configure_and_activate({'name': 'testy'})
        with open(version_path/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf, "")

    def test_static_folder_is_configured_in_nginx(self):
        version_path = self.configure_and_activate({
            'name': 'testy',
            'urlmap': [
                {'url': '/media',
                 'type': 'static',
                 'path': 'mymedia'},
            ],
        })
        with open(version_path/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "location /media { alias %s/mymedia; }" % version_path)

    def test_wsgi_app_is_configured_in_nginx(self):
        version_path = self.configure_and_activate({
            'name': 'testy',
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'wsgi_app': 'wsgiref.simple_server:demo_app'},
            ],
        })
        with open(version_path/'nginx-site.conf', 'rb') as f:
            nginx_conf = f.read()
        self.assert_equivalent(nginx_conf,
            "location / { "
            "    include /etc/nginx/fastcgi_params; "
            "    fastcgi_param PATH_INFO $fastcgi_script_name; "
            "    fastcgi_param SCRIPT_NAME ""; "
            "    fastcgi_pass unix:%(socket_path)s; "
            " }" % {'socket_path': version_path/'wsgi-app.sock'})
