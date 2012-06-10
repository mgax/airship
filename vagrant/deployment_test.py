import unittest
from StringIO import StringIO
import json
from fabric.api import env, run, sudo, put
from fabric.contrib.files import exists
from path import path


cfg = {}
cfg['sarge-home'] = path('/var/local/sarge')
cfg['sarge-venv'] = cfg['sarge-home']/'sandbox'


def provision():
    sudo("mkdir '%(sarge-home)s'" % cfg)
    sudo("virtualenv '%(sarge-venv)s' --no-site-packages" % cfg)
    sudo("'%(sarge-venv)s'/bin/pip install -r /sarge-src/requirements.txt" % cfg)
    sudo("'%(sarge-venv)s'/bin/pip install importlib argparse" % cfg)


def setUpModule():
    global sarge
    import sarge
    env['key_filename'] = path(__file__).parent/'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    if not exists(cfg['sarge-home']):
        provision()


def tearDownModule():
    from fabric.network import disconnect_all
    disconnect_all()


def remote_listdir(name):
    cmd = ("python -c 'import json,os; "
           "print json.dumps(os.listdir(\"%s\"))'" % name)
    return json.loads(run(cmd))


class VagrantDeploymentTest(unittest.TestCase):

    def setUp(self):
        self._orig_names = set(remote_listdir(cfg['sarge-home']))

    def tearDown(self):
        current_names = set(remote_listdir(cfg['sarge-home']))
        new_names = current_names - self._orig_names
        if 'supervisord.pid' in new_names:
            sudo("kill -9 `cat '%(sarge-home)s'/supervisord.pid`" % cfg)
        for name in new_names:
            sudo("rm -rf '%s'" % (cfg['sarge-home']/name,))

    def configure(self, config):
        put(StringIO(json.dumps(config)),
            str(cfg['sarge-home']/sarge.DEPLOYMENT_CFG),
            use_sudo=True)

    def test_ping(self):
        self.configure({'deployments': []})
        sudo("'%(sarge-venv)s'/bin/python /sarge-src/sarge.py "
              "'%(sarge-home)s' init" % cfg)
        sudo("'%(sarge-venv)s'/bin/supervisord "
             "-c '%(sarge-home)s'/supervisord.conf" % cfg)
        assert run('pwd') == '/home/vagrant'
