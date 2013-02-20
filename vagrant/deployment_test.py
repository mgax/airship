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
    "kv-0.2.zip",
]
VAGRANT_HOME = path('/home/vagrant')

env['sarge-home'] = path('/var/local/sarge-test')
env['sarge-src'] = '/sarge-src'
env['index-dir'] = VAGRANT_HOME / 'virtualenv-dist'
env['index-url'] = 'file://' + env['index-dir']


def update_index_dir():
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
        run("mkdir dist")
        run("cp {index-dir}/virtualenv.py dist/".format(**env))
        run("python dist/virtualenv.py --distribute "
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
        run("opt/sarge-venv/bin/airship . init")


def setUpModule(self):
    env['key_filename'] = path(__file__).parent / 'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    update_index_dir()
    if not exists(env['sarge-home']):
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


def get_buckets():
    json_list = run('{sarge-home}/bin/sarge list'.format(**env))
    return json.loads(json_list)['buckets']


def get_port(proc_name):
    for i in get_buckets():
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
        run('bin/sarge deploy _app.tar {proc_name}'
            .format(proc_name=proc_name))
        run('rm _app.tar')


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        run("{sarge-home}/bin/supervisord".format(**env), pty=False)
        _shutdown = "{sarge-home}/bin/supervisorctl shutdown".format(**env)
        self.addCleanup(run, _shutdown)
        run("echo '{{}}' > {sarge-home}/etc/airship.yaml".format(**env))

    def add_bucket_cleanup(self, proc_name):
        self.addCleanup(run, ('{sarge-home}/bin/sarge destroy {proc_name}'
                              .format(proc_name=proc_name, **env)))

    def test_deploy_sarge_bucket_answers_to_http(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_bucket_cleanup('web')

        self.assertEqual(get_from_port(get_port('web')).text, msg)

    def test_deploy_new_version_answers_on_different_port(self):
        msg = "hello sarge!"

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_bucket_cleanup('web')
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
            self.add_bucket_cleanup('web')

            deploy(tar_file, 'otherweb')
            self.add_bucket_cleanup('otherweb')

        self.assertEqual(get_from_port(get_port('web')).text, msg)
        self.assertEqual(get_from_port(get_port('otherweb')).text, msg)

    def test_apps_answer_on_configured_haproxy_ports(self):
        msg = "hello sarge!"

        sarge_yaml = {'port_map': {'web': '*:4998', 'otherweb': '*:4999'}}
        put(StringIO(json.dumps(sarge_yaml)),
            str(env['sarge-home'] / 'etc' / 'airship.yaml'))

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP.format(msg=msg))
            (tmp / 'Procfile').write_text("web: python theapp.py\n"
                                          "otherweb: python theapp.py\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_bucket_cleanup('web')

            deploy(tar_file, 'otherweb')
            self.add_bucket_cleanup('otherweb')

        self.assertEqual(get_from_port(4998).text, msg)
        self.assertEqual(get_from_port(4999).text, msg)

    def test_requirements_installed_in_virtualenv(self):
        sarge_yaml = {'python_dist': env['index-dir']}
        put(StringIO(json.dumps(sarge_yaml)),
            str(env['sarge-home'] / 'etc' / 'airship.yaml'))

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(
                'import os\n'
                'from wsgiref.simple_server import make_server\n'
                'from path import path\n'
                'msg = path.__doc__.split(".")[0].strip()\n'
                'def theapp(environ, start_response):\n'
                '    start_response("200 OK", [])\n'
                '    return [msg]\n'
                'port = int(os.environ["PORT"])\n'
                'make_server("0", port, theapp).serve_forever()\n'
            )
            (tmp / 'Procfile').write_text("web: python theapp.py\n")
            (tmp / 'requirements.txt').write_text("path.py==2.4\n")

        with cd(env['sarge-home']):
            deploy(tar_file, 'web')
            self.add_bucket_cleanup('web')

        self.assertEqual(get_from_port(get_port('web')).text,
                         "Represents a filesystem path")
