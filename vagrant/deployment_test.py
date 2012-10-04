import os
import unittest
import subprocess
import tempfile
from StringIO import StringIO
from contextlib import contextmanager
import json
from fabric.api import env, run, sudo, cd, put
from fabric.contrib.files import exists
from path import path
import requests


WEB_INDEX_URL = "http://grep.ro/quickpub/pypkg/"
PACKAGE_FILENAMES = [
    "virtualenv.py",
    "distribute-0.6.28.tar.gz",
    "pip-1.2.1.post1.zip",
    "wheel-0.9.7.tar.gz",
    "markerlib-0.5.2.tar.gz",
    "PyYAML-3.10-cp27-none-linux_x86_64.whl",
    "blinker-1.2-py27-none-any.whl",
    "meld3-0.6.9-py27-none-any.whl",
    "path.py-2.4-py27-none-any.whl",
    "supervisor-3.0b1-py27-none-any.whl",
    "kv-0.1-py27-none-any.whl",
]
VAGRANT_HOME = path('/home/vagrant')

env['sarge-home'] = path('/var/local/sarge-test')
env['sarge-src'] = '/sarge-src'
env['index-dir'] = VAGRANT_HOME / 'virtualenv-dist'
env['index-url'] = 'file://' + env['index-dir']


def update_virtualenv():
    run("mkdir -p {index-dir}".format(**env))
    with cd(env['index-dir']):
        for name in PACKAGE_FILENAMES:
            if not exists(name):
                run("curl -O {url}".format(url=WEB_INDEX_URL + name))

SARGE_REPO = path(__file__).parent.parent


def install_sarge():
    sudo("mkdir {sarge-home}".format(**env))
    with cd(env['sarge-home']):
        sudo("chown vagrant: .")
        run("mkdir opt")
        run("python {index-dir}/virtualenv.py --distribute "
            "--extra-search-dir={index-dir} --never-download "
            "opt/sarge-venv"
            .format(**env))
        run("opt/sarge-venv/bin/pip install wheel "
            "--no-index --find-links={index-url} "
            .format(**env))
        run("opt/sarge-venv/bin/pip install "
            "--use-wheel --no-index --find-links={index-url} "
            "-e {sarge-src}"
            .format(**env))
        run("opt/sarge-venv/bin/sarge . init")


def setUpModule(self):
    env['key_filename'] = path(__file__).parent / 'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    update_virtualenv()
    if os.environ.get("SARGE_TEST_REINSTALL") or not exists(env['sarge-home']):
        sudo("rm -rf {sarge-home}".format(**env))
        install_sarge()


def tearDownModule(self):
    from fabric.network import disconnect_all
    disconnect_all()


SIMPLE_APP = """\
import os
from wsgiref.simple_server import make_server
def theapp(environ, start_response):
    start_response("200 OK", [])
    return ["{msg}"]
make_server("0", int(os.environ['PORT']), theapp).serve_forever()
"""


DEPLOY_SCRIPT = """#!/usr/bin/env python
import os, sys, subprocess
import json
SARGE_HOME='{sarge-home}'
def sarge(*cmd):
    return subprocess.check_output([SARGE_HOME + '/bin/sarge'] + list(cmd))
for instance_info in json.loads(sarge('list'))['instances']:
    if instance_info['meta']['APPLICATION_NAME'] == 'web':
        print '=== destroying', instance_info['id']
        sarge('destroy', instance_info['id'])
instance_id = sarge('new', '{{"application_name": "web"}}').strip()
subprocess.check_call(['tar', 'xf', sys.argv[1], '-C', instance_id])
with open(instance_id + '/Procfile', 'rb') as f:
    procs = dict((k.strip(), v.strip()) for k, v in
                 (l.split(':', 1) for l in f))
with open(instance_id + '/server', 'wb') as f:
    f.write('exec %s\\n' % procs['web'])
    os.chmod(f.name, 0755)
sarge('start', instance_id)
"""


def retry(exceptions, func, *args, **kwargs):
    from time import time, sleep
    t0 = time()
    while time() - t0 < 5:
        try:
            return func(*args, **kwargs)
        except Exception, e:
            if not isinstance(e, tuple(exceptions)):
                raise
        sleep(.1)
    else:
        raise RuntimeError("Function keeps failing after trying for 5 seconds")


@contextmanager
def tar_maker():
    tmp = path(tempfile.mkdtemp())
    tar_file = StringIO()
    try:
        yield tmp, tar_file
        tar_data = subprocess.check_output(['tar cf - *'], shell=True, cwd=tmp)
        tar_file.write(tar_data)
        tar_file.seek(0)
    finally:
        tmp.rmtree()


def get_instances():
    json_list = run('{sarge-home}/bin/sarge list'.format(**env))
    return json.loads(json_list)['instances']


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        run("{sarge-home}/bin/supervisord".format(**env), pty=False)
        _shutdown = "{sarge-home}/bin/supervisorctl shutdown".format(**env)
        self.addCleanup(run, _shutdown)

    def insall_deploy_script(self):
        with cd(env['sarge-home']):
            put(StringIO(DEPLOY_SCRIPT.format(**env)), 'bin/deploy', mode=0755)
            self.addCleanup(run, 'rm {sarge-home}/bin/deploy'.format(**env))

    def test_deploy_sarge_instance_answers_to_http(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        self.insall_deploy_script()

        with cd(env['sarge-home']):
            put(tar_file, '_app.tar')
            self.addCleanup(run, 'rm {sarge-home}/_app.tar'.format(**env))

            run('bin/deploy _app.tar web')

            _destroy = '{sarge-home}/bin/sarge destroy web'.format(**env)
            self.addCleanup(run, _destroy)

        port = get_instances()[0]['port']
        url = 'http://192.168.13.13:{port}/'.format(port=port)
        response = retry([requests.ConnectionError], requests.get, url)
        self.assertEqual(response.text, msg)

    def test_deploy_new_version_answers_on_different_port(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        self.insall_deploy_script()

        with cd(env['sarge-home']):
            put(tar_file, '_app.tar')
            self.addCleanup(run, 'rm {sarge-home}/_app.tar'.format(**env))

            run('bin/deploy _app.tar web')
            port1 = get_instances()[0]['port']

            run('bin/deploy _app.tar web')
            port2 = get_instances()[0]['port']

        _destroy = '{sarge-home}/bin/sarge destroy web'.format(**env)
        self.addCleanup(run, _destroy)

        self.assertNotEqual(port1, port2)

        url = 'http://192.168.13.13:{port}/'.format(port=port2)
        response = retry([requests.ConnectionError], requests.get, url)
        self.assertEqual(response.text, msg)
