import os
import unittest
import subprocess
from StringIO import StringIO
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
    "PyYAML-3.10-cp26-none-linux_i686.whl",
    "blinker-1.2-py26-none-any.whl",
    "importlib-1.0.2-py26-none-any.whl",
    "meld3-0.6.9-py26-none-any.whl",
    "path.py-2.4-py26-none-any.whl",
    "supervisor-3.0b1-py26-none-any.whl",
    "argparse-1.2.1-py26-none-any.whl",
]
VAGRANT_HOME = path('/home/vagrant')

env['sarge-home'] = path('/var/local/sarge-test')
env['sarge-src'] = VAGRANT_HOME / 'sarge'
env['index-dir'] = VAGRANT_HOME / 'virtualenv-dist'
env['index-url'] = 'file://' + env['index-dir']


def update_virtualenv():
    run("mkdir -p {index-dir}".format(**env))
    with cd(env['index-dir']):
        for name in PACKAGE_FILENAMES:
            if not exists(name):
                run("curl -O {url}".format(url=WEB_INDEX_URL + name))

SARGE_REPO = path(__file__).parent.parent


def upload_src():
    src = subprocess.check_output(['git', 'archive', 'HEAD'], cwd=SARGE_REPO)
    run("rm -rf {sarge-src}; mkdir -p {sarge-src}".format(**env))
    with cd(env['sarge-src']):
        put(StringIO(src), '_src.tar')
        run("tar xf _src.tar")
        run("rm _src.tar")


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
        upload_src()
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


SIMPLE_APP = """#!/usr/bin/env python
from wsgiref.simple_server import make_server
def theapp(environ, start_response):
    start_response("200 OK", [])
    return ["{response_data}"]
make_server("0", {port}, theapp).serve_forever()
"""


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        run("{sarge-home}/bin/supervisord".format(**env))

    def tearDown(self):
        run("{sarge-home}/bin/supervisorctl shutdown".format(**env))

    def test_deploy_sarge_instance_answers_to_http(self):
        testdata = {
            'response_data': "hello sarge!",
            'port': 5005,
        }
        with cd(env['sarge-home']):
            instance_id = run('bin/sarge new \'{"application_name": "web"}\' '
                              '2> /dev/null')
            with cd(env['sarge-home'] / instance_id):
                code = SIMPLE_APP.format(**testdata)
                put(StringIO(code), 'server', mode=0755)
            run('bin/sarge start web')

        import time; time.sleep(0.5)
        response = requests.get('http://192.168.13.13:{port}/'
                                .format(**testdata))
        self.assertEqual(response.text, testdata['response_data'])

        with cd(env['sarge-home']):
            run('bin/sarge destroy web'.format(**env))
