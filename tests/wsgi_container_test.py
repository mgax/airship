import unittest
import tempfile
import json
from path import path
from mock import patch, call


def setUpModule(self):
    global sarge, _subprocess_patch, mock_subprocess
    import sarge
    _subprocess_patch = patch('sarge.subprocess')
    mock_subprocess = _subprocess_patch.start()


def tearDownModule(self):
    _subprocess_patch.stop()


def invoke_wsgi_app(app, environ):
    response = {}
    def start_response(status, headers):
        response['status'] = status
        response['headers'] = headers
    data = app(environ, start_response)
    response['data'] = ''.join(data)
    return response


def get_fcgi_response(socket_path, environ):
    from wsgiref.util import setup_testing_defaults
    from flup.client.fcgi_app import FCGIApp
    app = FCGIApp(connect=str(socket_path))
    setup_testing_defaults(environ)
    return invoke_wsgi_app(app, environ)


def wait_for(callback, sleep_time, ticks):
    import time
    for c in xrange(ticks):
        if callback():
            return True
        time.sleep(sleep_time)
    else:
        return False


def read_config(cfg_path):
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


class WsgiContainerTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    def popen_with_cleanup(self, *args, **kwargs):
        import subprocess
        p = subprocess.Popen(*args, **kwargs)
        # cleanups are called in reverse order; first kill, then wait
        self.addCleanup(p.wait)
        self.addCleanup(p.kill)

    def test_wsgi_app_works_via_fcgi(self):
        self.configure({
            'plugins': ['sarge:NginxPlugin'],
            'deployments': [{'name': 'testy'}],
        })

        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = path(testy.new_version())
        app_config = {
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'wsgi_app': 'wsgiref.simple_server:demo_app'},
            ],
        }
        with open(version_folder/'sargeapp.yaml', 'wb') as f:
            json.dump(app_config, f)
        testy.activate_version(version_folder)

        config = read_config(self.tmp/sarge.SUPERVISORD_CFG)
        command = config.get('program:testy', 'command')

        self.popen_with_cleanup(command, cwd=version_folder, shell=True)

        socket_path = version_folder/'wsgi-app.sock'
        if not wait_for(socket_path.exists, 0.01, 500):
            self.fail('No socket found after 5 seconds')

        msg = "the-matrix-has-you"
        response = get_fcgi_response(socket_path, {'PATH_INFO': msg})

        self.assertIn(msg, response['data'])
