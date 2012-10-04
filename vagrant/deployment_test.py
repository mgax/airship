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


HAPROXY_GLOBAL = """\
global
    maxconn 256

defaults
    mode http
    timeout connect  5000ms
    timeout client  50000ms
    timeout server  50000ms

"""


SUPERVISORD_HAPROXY = """\
[program:haproxy]
redirect_stderr = true
stdout_logfile = /var/local/sarge-test/var/log/haproxy.log
startsecs = 0
startretries = 1
autostart = true
command = /usr/sbin/haproxy -f /var/local/sarge-test/var/haproxy/haproxy.cfg
"""


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
        run("mkdir var/haproxy")
        run("mkdir var/haproxy/bits")
        put(StringIO(HAPROXY_GLOBAL), "var/haproxy/bits/0-global")
        put(StringIO(HAPROXY_GLOBAL), "var/haproxy/haproxy.cfg")
        put(StringIO(SUPERVISORD_HAPROXY), "etc/supervisor.d/haproxy")


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
from path import path
os.chdir('{sarge-home}')
var_haproxy = path('var/haproxy')
def update_haproxy():
    subprocess.check_call(['cat bits/* > haproxy.cfg'],
                          shell=True, cwd=var_haproxy)
    subprocess.check_call(['bin/supervisorctl', 'restart', 'haproxy'])
def sarge(*cmd):
    return subprocess.check_output(['bin/sarge'] + list(cmd))
public_ports_path = path('etc/public_ports.json')
if public_ports_path.isfile():
    public_ports = json.loads(public_ports_path.bytes())
else:
    public_ports = {{}}
proc_name = sys.argv[2]
for instance_info in json.loads(sarge('list'))['instances']:
    if instance_info['meta']['APPLICATION_NAME'] == proc_name:
        print '=== destroying', instance_info['id']
        sarge('destroy', instance_info['id'])
        haproxy_bit = var_haproxy / 'bits' / proc_name
        if haproxy_bit.isfile():
            subprocess.check_call(['rm', haproxy_bit])
            update_haproxy()
instance_cfg = {{'application_name': proc_name}}
instance_id = sarge('new', json.dumps(instance_cfg)).strip()
subprocess.check_call(['tar', 'xf', sys.argv[1], '-C', instance_id])
with open(instance_id + '/Procfile', 'rb') as f:
    procs = dict((k.strip(), v.strip()) for k, v in
                 (l.split(':', 1) for l in f))
with open(instance_id + '/server', 'wb') as f:
    f.write('exec %s\\n' % procs[proc_name])
    os.chmod(f.name, 0755)
sarge('start', instance_id)
if proc_name in public_ports:
    port = json.loads(sarge('list'))['instances'][0]['port']
    public_port = public_ports[proc_name]
    with open(var_haproxy / 'bits' / proc_name, 'wb') as f:
        f.write('listen {{proc_name}}\\n'.format(**locals()))
        f.write('  bind *:{{public_port}}\\n'.format(**locals()))
        f.write('  server {{proc_name}}1 127.0.0.1:{{port}} maxconn 32\\n'
                .format(**locals()))
    update_haproxy()
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


def get_port(proc_name):
    for i in get_instances():
        if i['meta']['APPLICATION_NAME'] == proc_name:
            return i['port']
    else:
        raise RuntimeError("No process found with name %r" % proc_name)


def get_from_port(port):
    url = 'http://192.168.13.13:{port}/'.format(port=port)
    return retry([requests.ConnectionError], requests.get, url)


def deploy(tar_file, proc_name):
    with cd(env['sarge-home']):
        put(tar_file, '_app.tar')
        run('opt/sarge-venv/bin/python bin/deploy _app.tar {proc_name}'
            .format(proc_name=proc_name))
        run('rm _app.tar')


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        run("{sarge-home}/bin/supervisord".format(**env), pty=False)
        _shutdown = "{sarge-home}/bin/supervisorctl shutdown".format(**env)
        self.addCleanup(run, _shutdown)
        self.insall_deploy_script()

    def insall_deploy_script(self):
        with cd(env['sarge-home']):
            put(StringIO(DEPLOY_SCRIPT.format(**env)), 'bin/deploy', mode=0755)
            self.addCleanup(run, 'rm {sarge-home}/bin/deploy'.format(**env))

    def add_instance_cleanup(self, proc_name):
        self.addCleanup(run, ('{sarge-home}/bin/sarge destroy {proc_name}'
                              .format(proc_name=proc_name, **env)))

    def test_deploy_sarge_instance_answers_to_http(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_instance_cleanup('web')

        self.assertEqual(get_from_port(get_port('web')).text, msg)

    def test_deploy_new_version_answers_on_different_port(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_instance_cleanup('web')
            port1 = get_port('web')

            deploy(tar_file, 'web')
            port2 = get_port('web')

        self.assertNotEqual(port1, port2)
        self.assertEqual(get_from_port(port2).text, msg)

    def test_deploy_non_web_process_does_not_clobber_web_process(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n"
                                          "otherweb: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_instance_cleanup('web')

            deploy(tar_file, 'otherweb')
            self.add_instance_cleanup('otherweb')

        self.assertEqual(get_from_port(get_port('web')).text, msg)
        self.assertEqual(get_from_port(get_port('otherweb')).text, msg)

    def test_apps_answer_on_configured_haproxy_ports(self):
        msg = "hello sarge!"

        public_ports_path = env['sarge-home'] / 'etc' / 'public_ports.json'
        public_ports = {'web': 4998, 'otherweb': 4999}
        put(StringIO(json.dumps(public_ports)), str(public_ports_path))
        self.addCleanup(run, 'rm ' + public_ports_path)

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n"
                                          "otherweb: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_instance_cleanup('web')

            deploy(tar_file, 'otherweb')
            self.add_instance_cleanup('otherweb')

        self.assertEqual(get_from_port(4998).text, msg)
        self.assertEqual(get_from_port(4999).text, msg)
