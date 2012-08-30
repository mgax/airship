import unittest
from StringIO import StringIO
import json
import urllib
from fabric.api import env, run, sudo, put, cd
from fabric.contrib.files import exists
from path import path


env['sarge-home'] = path('/var/local/sarge')
env['sarge-venv'] = path('/var/local/sarge-sandbox')


def provision():
    sudo("virtualenv '%(sarge-venv)s' --no-site-packages" % env)
    sudo("'%(sarge-venv)s'/bin/pip install -e /sarge-src" % env)
    sudo("'%(sarge-venv)s'/bin/pip install flup" % env)


def setUpModule(self):
    env['key_filename'] = path(__file__).parent / 'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    if not exists(env['sarge-venv']):
        provision()

    sudo("rm -rf '%(sarge-home)s'" % env)
    self._nginx_symlink = '/etc/nginx/sites-enabled/testy'


def tearDownModule(self):
    sudo("rm -f %s" % self._nginx_symlink)
    from fabric.network import disconnect_all
    disconnect_all()


def sarge_cmd(cmd):
    base = ("'%(sarge-venv)s'/bin/sarge '%(sarge-home)s' " % env)
    return run(base + cmd)


def supervisorctl_cmd(cmd):
    base = ("'%(sarge-venv)s'/bin/supervisorctl "
            "-c '%(sarge-home)s'/etc/supervisor.conf " % env)
    return run(base + cmd)


def remote_listdir(name):
    cmd = ("python -c 'import json,os; "
           "print json.dumps(os.listdir(\"%s\"))'" % name)
    return json.loads(run(cmd))


def put_json(data, remote_path, **kwargs):
    return put(StringIO(json.dumps(data)), str(remote_path), **kwargs)


def get_url(url):
    f = urllib.urlopen(url)
    try:
        return f.read()
    finally:
        f.close()


def quote_json(config):
    data = json.dumps(config)
    for ch in ['\\', '"', '$', '`']:
        data = data.replace(ch, '\\\\' + ch)
    return '"' + data + '"'


def link_in_nginx(id_):
    urlmap_path = env['sarge-home'] / 'etc' / 'nginx' / (id_ + '-urlmap')
    nginx_cfg = "server { listen 8013; include %s; }\n" % urlmap_path
    put(StringIO(nginx_cfg), _nginx_symlink, use_sudo=True)


class VagrantDeploymentTest(unittest.TestCase):

    def setUp(self):
        sudo("mkdir '%(sarge-home)s'" % env)
        sudo("chown vagrant: '%(sarge-home)s'" % env)
        run("mkdir '%(sarge-home)s'/etc" % env)
        put_json({'plugins': ['sarge:NginxPlugin', 'sarge:ListenPlugin']},
                 env['sarge-home'] / 'etc' / 'sarge.yaml',
                 use_sudo=True)
        sarge_cmd("init")
        run("'%(sarge-venv)s'/bin/supervisord "
            "-c '%(sarge-home)s'/etc/supervisor.conf" % env)

    def tearDown(self):
        supervisorctl_cmd("shutdown")
        sudo("rm -rf '%(sarge-home)s'" % env)

    def test_ping(self):
        assert run('pwd') == '/home/vagrant'

    def test_deploy_simple_wsgi_app(self):
        cfg = {'urlmap': [{'type': 'wsgi',
                           'url': '/',
                           'app_factory': 'mytinyapp:gettheapp'}]}
        instance_id = sarge_cmd("new " + quote_json(cfg)).strip()

        app_py = ('def gettheapp(appcfg):\n'
                  '    def theapp(environ, start_response):\n'
                  '        start_response("200 OK", [])\n'
                  '        return ["hello sarge!\\n"]\n'
                  '    return theapp\n')
        put(StringIO(app_py),
            str(env['sarge-home'] / instance_id / 'mytinyapp.py'))
        sarge_cmd("start '%s'" % instance_id)
        link_in_nginx(instance_id)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge!\n")

    def test_deploy_new_instance(self):
        cfg = {'urlmap': [{'type': 'wsgi',
                           'url': '/',
                           'app_factory': 'mytinyapp:gettheapp'}]}
        app_py_tmpl = ('def gettheapp(appcfg):\n'
                       '    def theapp(environ, start_response):\n'
                       '        start_response("200 OK", [])\n'
                       '        return ["hello sarge %s!\\n"]\n'
                       '    return theapp\n')

        # deploy instance one
        instance_id_1 = sarge_cmd("new " + quote_json(cfg)).strip()
        put(StringIO(app_py_tmpl % 'one'),
            str(env['sarge-home'] / instance_id_1 / 'mytinyapp.py'))
        sarge_cmd("start '%s'" % instance_id_1)
        link_in_nginx(instance_id_1)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge one!\n")

        # deploy instance two
        instance_id_2 = sarge_cmd("new " + quote_json(cfg)).strip()
        put(StringIO(app_py_tmpl % 'two'),
            str(env['sarge-home'] / instance_id_2 / 'mytinyapp.py'))
        sarge_cmd("start '%s'" % instance_id_2)
        link_in_nginx(instance_id_2)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge two!\n")

    def test_deploy_php(self):
        cfg = {'urlmap': [{'type': 'php', 'url': '/'}]}
        instance_id = sarge_cmd("new " + quote_json(cfg)).strip()

        app_php = ('<?php echo "hello from" . " PHP!\\n"; ?>')
        put(StringIO(app_php),
            str(env['sarge-home'] / instance_id / 'someapp.php'))
        sarge_cmd("start '%s'" % instance_id)
        link_in_nginx(instance_id)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/someapp.php'),
                         "hello from PHP!\n")

    def test_deploy_static_site(self):
        cfg = {'urlmap': [{'type': 'static', 'url': '/', 'path': ''}]}
        instance_id = sarge_cmd("new " + quote_json(cfg)).strip()

        with cd(str(env['sarge-home'] / instance_id)):
            run("echo 'hello static!' > hello.html")
            run("mkdir sub")
            run("echo 'submarine' > sub/marine.txt")

        sarge_cmd("start '%s'" % instance_id)
        link_in_nginx(instance_id)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/hello.html'),
                         "hello static!\n")

        self.assertEqual(get_url('http://192.168.13.13:8013/sub/marine.txt'),
                         "submarine\n")

    def test_start_server_using_default_executable_name(self):
        cfg = {'urlmap': [{'type': 'proxy',
                           'url': '/',
                           'upstream_url': 'http://localhost:43423'}]}
        instance_id = sarge_cmd("new " + quote_json(cfg)).strip()

        app_py = ('#!/usr/bin/env python\n'
                  'from wsgiref.simple_server import make_server\n'
                  'def theapp(environ, start_response):\n'
                  '    start_response("200 OK", [])\n'
                  '    return ["hello sarge!\\n"]\n'
                  'make_server("0", 43423, theapp).serve_forever()\n')
        put(StringIO(app_py),
            str(env['sarge-home'] / instance_id / 'server'),
            mode=0755)
        sarge_cmd("start '%s'" % instance_id)
        link_in_nginx(instance_id)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge!\n")

    def test_list_instances_contains_enough_info_to_clean_up(self):
        sarge_cmd("new " + quote_json({'application_name': 'testy'}))
        report_1 = json.loads(sarge_cmd("list"))
        self.assertEqual(len(report_1['instances']), 1)
        instance_id = report_1['instances'][0]['id']
        sarge_cmd("destroy " + instance_id)
        report_2 = json.loads(sarge_cmd("list"))
        self.assertEqual(len(report_2['instances']), 0)
