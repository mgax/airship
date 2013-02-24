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

env['airship-home'] = path('/var/local/airship-test')
env['airship-src'] = '/airship-src'
env['index-dir'] = VAGRANT_HOME / 'virtualenv-dist'
env['index-url'] = 'file://' + env['index-dir']


def update_index_dir():
    run("mkdir -p {index-dir}".format(**env))
    with cd(env['index-dir']):
        for name in PACKAGE_FILENAMES:
            if not exists(name):
                run("curl -O {url}".format(url=WEB_INDEX_URL + name))


def install_airship():
    sudo("mkdir {airship-home}".format(**env))
    with cd(env['airship-home']):
        sudo("chown vagrant: .")
        run("mkdir opt")
        run("mkdir dist")
        run("cp {index-dir}/virtualenv.py dist/".format(**env))
        run("python dist/virtualenv.py --distribute "
            "--extra-search-dir={index-dir} --never-download "
            "opt/airship-venv"
            .format(**env))
        run("opt/airship-venv/bin/pip install wheel "
            "--no-index --find-links={index-url} "
            .format(**env))
        run("opt/airship-venv/bin/pip install "
            "--use-wheel --no-index --find-links={index-url} "
            "-e {airship-src}"
            .format(**env))
        run("opt/airship-venv/bin/airship . init")


def setUpModule(self):
    env['key_filename'] = path(__file__).parent / 'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    update_index_dir()
    if not exists(env['airship-home']):
        install_airship()


def tearDownModule(self):
    from fabric.network import disconnect_all
    disconnect_all()


SIMPLE_APP = """\
import os, sys
from wsgiref.simple_server import make_server
def theapp(environ, start_response):
    start_response("200 OK", [])
    return ["hello " + sys.argv[-1]]
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


def cleanup_all_buckets():
    json_list = run('{airship-home}/bin/airship list'.format(**env))
    for bucket in json.loads(json_list)['buckets']:
        run('{airship-home}/bin/airship destroy -d {bucket_id}'
            .format(bucket_id=bucket['id'], **env))


def get_from_port(port):
    url = 'http://192.168.13.13:{port}/'.format(port=port)
    return retry([requests.ConnectionError], requests.get, url)


def deploy(tar_file):
    with cd(env['airship-home']):
        put(tar_file, '_app.tar')
        run('bin/airship deploy _app.tar')
        run('rm _app.tar')


def configure_airship(config):
    put(StringIO(json.dumps(config)),
        str(env['airship-home'] / 'etc' / 'airship.yaml'))


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        run("{airship-home}/bin/supervisord".format(**env), pty=False)
        _shutdown = "{airship-home}/bin/supervisorctl shutdown".format(**env)
        self.addCleanup(run, _shutdown)
        self.addCleanup(cleanup_all_buckets)
        configure_airship({'port_map': {'web': '5016'}})

    def test_deploy_airship_bucket_answers_to_http(self):
        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP)
            (tmp / 'Procfile').write_text("web: python theapp.py\n")

        with cd(env['airship-home']):
            deploy(tar_file)

        self.assertEqual(get_from_port(5016).text, "hello theapp.py")

    def test_deploy_non_web_process_does_not_clobber_web_process(self):
        configure_airship({'port_map': {'web': '4998', 'otherweb': '4999'}})

        with tar_maker() as (tmp, tar_file):
            (tmp / 'theapp.py').write_text(SIMPLE_APP)
            (tmp / 'Procfile').write_text("web: python theapp.py 1\n"
                                          "otherweb: python theapp.py 2\n")

        with cd(env['airship-home']):
            deploy(tar_file)
            deploy(tar_file)

        self.assertEqual(get_from_port(4998).text, "hello 1")
        self.assertEqual(get_from_port(4999).text, "hello 2")

    def test_requirements_installed_in_virtualenv(self):
        configure_airship({
            'python_dist': env['index-dir'],
            'port_map': {'web': '5016'},
        })

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

        with cd(env['airship-home']):
            deploy(tar_file)

        self.assertEqual(get_from_port(5016).text,
                         "Represents a filesystem path")
