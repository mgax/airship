import unittest
from StringIO import StringIO
import json
import urllib
from fabric.api import env, run, sudo, put
from fabric.contrib.files import exists
from path import path


cfg = {}
cfg['sarge-home'] = path('/var/local/sarge')
cfg['sarge-venv'] = path('/var/local/sarge-sandbox')


def provision():
    sudo("virtualenv '%(sarge-venv)s' --no-site-packages" % cfg)
    sudo("'%(sarge-venv)s'/bin/pip install -r /sarge-src/requirements.txt" % cfg)
    sudo("'%(sarge-venv)s'/bin/pip install importlib argparse" % cfg)


def setUpModule(self):
    import sarge; self.sarge = sarge
    env['key_filename'] = path(__file__).parent/'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    if not exists(cfg['sarge-venv']):
        provision()

    self._nginx_symlink = '/etc/nginx/sites-enabled/testy'
    nginx_all_sites = cfg['sarge-home']/'nginx.plugin'/'all_sites.conf'
    sudo("ln -s '%s' '%s'" % (nginx_all_sites, self._nginx_symlink))


def tearDownModule(self):
    sudo("rm %s" % self._nginx_symlink)
    from fabric.network import disconnect_all
    disconnect_all()


def sarge_cmd(cmd):
    base = ("'%(sarge-venv)s'/bin/python "
            "/sarge-src/sarge.py '%(sarge-home)s' " % cfg)
    return sudo(base + cmd)

def supervisorctl_cmd(cmd):
    base = ("'%(sarge-venv)s'/bin/supervisorctl "
            "-c '%(sarge-home)s'/supervisord.conf " % cfg)
    return sudo(base + cmd)


def remote_listdir(name):
    cmd = ("python -c 'import json,os; "
           "print json.dumps(os.listdir(\"%s\"))'" % name)
    return json.loads(run(cmd))


def put_json(data, remote_path, **kwargs):
    return put(StringIO(json.dumps(data)), str(remote_path), **kwargs)


def get_url(url):
    f = urllib.urlopen('http://192.168.13.13:8013/')
    try:
        return f.read()
    finally:
        f.close()


class VagrantDeploymentTest(unittest.TestCase):

    def setUp(self):
        sudo("mkdir '%(sarge-home)s'" % cfg)
        put_json({'plugins': ['sarge:NginxPlugin']},
                 cfg['sarge-home']/sarge.DEPLOYMENT_CFG,
                 use_sudo=True)
        sarge_cmd("init")
        sudo("'%(sarge-venv)s'/bin/supervisord "
             "-c '%(sarge-home)s'/supervisord.conf" % cfg)

    def tearDown(self):
        supervisorctl_cmd("shutdown")
        sudo("rm -rf '%(sarge-home)s'" % cfg)

    def test_ping(self):
        assert run('pwd') == '/home/vagrant'

    def test_deploy_simple_wsgi_app(self):
        put_json({'name': 'testy'},
                 cfg['sarge-home']/sarge.DEPLOYMENT_CFG_DIR/'testy.yaml',
                 use_sudo=True)

        version_folder = path(sarge_cmd("new_version testy"))

        url_cfg = {
            'type': 'wsgi',
            'url': '/',
            'wsgi_app': 'mytinyapp:theapp',
        }
        put_json({'urlmap': [url_cfg], 'nginx_options': {'listen': '8013'}},
                 version_folder/'sargeapp.yaml', use_sudo=True)
        app_py = ('def theapp(environ, start_response):\n'
                  '    start_response("200 OK", [])\n'
                  '    return ["hello sarge!\\n"]\n')
        put(StringIO(app_py), str(version_folder/'mytinyapp.py'), use_sudo=True)
        sarge_cmd("activate_version testy '%s'" % version_folder)

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge!\n")
