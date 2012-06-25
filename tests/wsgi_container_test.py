from utils import unittest
import tempfile
import json
from path import path
from mock import patch, call
from utils import configure_sarge, configure_deployment, username


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


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

        configure_sarge(self.tmp, {'plugins': ['sarge:NginxPlugin']})
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})

        self.sarge = sarge.Sarge(self.tmp)
        self.testy = self.sarge.get_deployment('testy')
        self.version_folder = path(self.testy.new_version())

    def popen_with_cleanup(self, *args, **kwargs):
        import subprocess
        p = subprocess.Popen(*args, **kwargs)
        # cleanups are called in reverse order; first kill, then wait
        self.addCleanup(p.wait)
        self.addCleanup(p.kill)

    def start_app(self):
        cfg_folder = path(self.version_folder + '.cfg')
        config = read_config(cfg_folder/sarge.SUPERVISOR_DEPLOY_CFG)
        command = config.get('program:testy', 'command')
        self.popen_with_cleanup(command, cwd=self.version_folder, shell=True)

        run_folder = path(self.version_folder + '.run')
        socket_path = run_folder/'wsgi-app.sock'
        if not wait_for(socket_path.exists, 0.01, 500):
            self.fail('No socket found after 5 seconds')

        return socket_path

    def test_wsgi_app_works_via_fcgi(self):
        with (self.version_folder/'testyapp.py').open('wb') as f:
            f.write("def testy_app_factory(appcfg):\n"
                    "  def app(environ, start_response):\n"
                    "    start_response('200 OK', [])\n"
                    "    return ['the matrix has you.']\n"
                    "  return app\n")
        app_config = {
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'app_factory': 'testyapp:testy_app_factory'},
            ],
        }
        with open(self.version_folder/'sargeapp.yaml', 'wb') as f:
            json.dump(app_config, f)

        self.testy.activate_version(self.version_folder)

        socket_path = self.start_app()
        response = get_fcgi_response(socket_path, {'PATH_INFO': '/'})
        self.assertIn('the matrix has you', response['data'])

    def test_app_receives_configuration(self):
        with (self.version_folder/'testyapp.py').open('wb') as f:
            f.write("def testy_app_factory(appcfg):\n"
                    "  def app(environ, start_response):\n"
                    "    start_response('200 OK', [])\n"
                    "    return [appcfg.get('hidden', 'no message :(')]\n"
                    "  return app\n")
        app_config = {
            'urlmap': [
                {'url': '/',
                 'type': 'wsgi',
                 'app_factory': 'testyapp:testy_app_factory'},
            ],
        }
        with open(self.version_folder/'sargeapp.yaml', 'wb') as f:
            json.dump(app_config, f)

        @self.sarge.on_activate_version.connect
        def set_message(depl, appcfg, **extra):
            appcfg['hidden'] = "XKCD"

        self.testy.activate_version(self.version_folder)

        socket_path = self.start_app()
        response = get_fcgi_response(socket_path, {'PATH_INFO': '/'})
        self.assertIn("XKCD", response['data'])
