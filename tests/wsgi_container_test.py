import unittest
import tempfile
import json
from StringIO import StringIO
from path import path
from mock import patch, call


def setUpModule(self):
    global sarge
    import sarge


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


class WorkflowTest(unittest.TestCase):

    def setUp(self):
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)
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
        depl_config = {
            'name': 'testy',
            'tmp-wsgi-app': 'wsgiref.simple_server:demo_app',
        }
        self.configure({'deployments': [depl_config]})

        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_path = path(testy.new_version())
        testy.activate_version(version_path)

        config = read_config(self.tmp/sarge.SUPERVISORD_CFG)
        command = config.get('program:testy', 'command')

        self.popen_with_cleanup(command, cwd=version_path, shell=True)

        socket_path = version_path/'sock.fcgi'
        if not wait_for(socket_path.exists, 0.01, 500):
            self.fail('No socket found after 5 seconds')

        msg = "the-matrix-has-you"
        response = get_fcgi_response(socket_path, {'PATH_INFO': msg})

        self.assertIn(msg, response['data'])


class SupervisorInvocationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        (self.tmp/sarge.DEPLOYMENT_CFG).write_bytes('{"deployments": []}')

    @patch('sarge.subprocess')
    def test_invoke_supervisorctl(self, mock_subprocess):
        s = sarge.Sarge(self.tmp)
        s.supervisorctl(['hello', 'world!'])
        self.assertEqual(mock_subprocess.check_call.mock_calls,
                         [call(['supervisorctl',
                                '-c', self.tmp/sarge.SUPERVISORD_CFG,
                                'hello', 'world!'])])


class ShellTest(unittest.TestCase):

    def setUp(self):
        supervisorctl_patch = patch('sarge.Sarge.supervisorctl')
        self.mock_supervisorctl = supervisorctl_patch.start()
        self.addCleanup(supervisorctl_patch.stop)
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def configure(self, config):
        with open(self.tmp/sarge.DEPLOYMENT_CFG, 'wb') as f:
            json.dump(config, f)

    @patch('sarge.Deployment.new_version')
    def test_new_version_calls_api_method(self, mock_new_version):
        mock_new_version.return_value = "path-to-new-version"
        self.configure({'deployments': [{'name': 'testy'}]})
        mock_stdout = StringIO()
        with patch('sys.stdout', mock_stdout):
            sarge.main([str(self.tmp), 'new_version', 'testy'])
        self.assertEqual(mock_new_version.mock_calls, [call()])
        self.assertEqual(mock_stdout.getvalue().strip(), "path-to-new-version")

    @patch('sarge.Deployment.activate_version')
    def test_activate_version_calls_api_method(self, mock_activate_version):
        self.configure({'deployments': [{'name': 'testy', 'command': 'echo'}]})
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = path(testy.new_version())
        sarge.main([str(self.tmp), 'activate_version',
                    'testy', str(version_folder)])
        self.assertEqual(mock_activate_version.mock_calls,
                         [call(version_folder)])
        path_arg = mock_activate_version.mock_calls[0][1][0]
        self.assertIsInstance(path_arg, path)

    @patch('sarge.Deployment.start')
    def test_start_calls_api_method(self, mock_start):
        self.configure({'deployments': [{'name': 'testy'}]})
        sarge.main([str(self.tmp), 'start', 'testy'])
        self.assertEqual(mock_start.mock_calls, [call()])

    @patch('sarge.Deployment.stop')
    def test_stop_calls_api_method(self, mock_stop):
        self.configure({'deployments': [{'name': 'testy'}]})
        sarge.main([str(self.tmp), 'stop', 'testy'])
        self.assertEqual(mock_stop.mock_calls, [call()])

    def test_init_creates_configuration(self):
        self.configure({'deployments': []})
        self.assertItemsEqual([f.name for f in self.tmp.listdir()],
                              [sarge.DEPLOYMENT_CFG])
        sarge.main([str(self.tmp), 'init'])
        self.assertItemsEqual([f.name for f in self.tmp.listdir()],
                              [sarge.DEPLOYMENT_CFG, sarge.SUPERVISORD_CFG])
