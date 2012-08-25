import unittest
from StringIO import StringIO
import json
import urllib
from fabric.api import env, run, sudo, put, cd
from fabric.contrib.files import exists
from path import path


cfg = {}
cfg['sarge-home'] = path('/var/local/sarge')
cfg['sarge-venv'] = path('/var/local/sarge-sandbox')


def provision():
    sudo("virtualenv '%(sarge-venv)s' --no-site-packages" % cfg)
    sudo("'%(sarge-venv)s'/bin/pip install -e /sarge-src" % cfg)
    sudo("'%(sarge-venv)s'/bin/pip install flup" % cfg)


def setUpModule(self):
    env['key_filename'] = path(__file__).parent / 'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'
    if not exists(cfg['sarge-venv']):
        provision()

    sudo("rm -rf '%(sarge-home)s'" % cfg)
    self._nginx_symlink = '/etc/nginx/sites-enabled/testy'


def tearDownModule(self):
    sudo("rm -f %s" % self._nginx_symlink)
    from fabric.network import disconnect_all
    disconnect_all()


def sarge_cmd(cmd):
    base = ("'%(sarge-venv)s'/bin/sarge '%(sarge-home)s' " % cfg)
    return run(base + cmd)


def supervisorctl_cmd(cmd):
    base = ("'%(sarge-venv)s'/bin/supervisorctl "
            "-c '%(sarge-home)s'/etc/supervisor.conf " % cfg)
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


def quote_config(config):
    data = json.dumps(config)
    for ch in ['\\', '"', '$', '`']:
        data = data.replace(ch, '\\\\' + ch)
    return '"' + data + '"'


def link_in_nginx(id_):
    urlmap_path = cfg['sarge-home'] / 'etc' / 'nginx' / (id_ + '-urlmap')
    nginx_cfg = "server { listen 8013; include %s; }\n" % urlmap_path
    put(StringIO(nginx_cfg), _nginx_symlink, use_sudo=True)


class VagrantDeploymentTest(unittest.TestCase):

    def setUp(self):
        sudo("mkdir '%(sarge-home)s'" % cfg)
        sudo("chown vagrant: '%(sarge-home)s'" % cfg)
        run("mkdir '%(sarge-home)s'/etc" % cfg)
        put_json({'plugins': ['sarge:NginxPlugin']},
                 cfg['sarge-home'] / 'etc' / 'sarge.yaml',
                 use_sudo=True)
        sarge_cmd("init")
        run("'%(sarge-venv)s'/bin/supervisord "
            "-c '%(sarge-home)s'/etc/supervisor.conf" % cfg)

    def tearDown(self):
        supervisorctl_cmd("shutdown")
        sudo("rm -rf '%(sarge-home)s'" % cfg)

    def test_ping(self):
        assert run('pwd') == '/home/vagrant'

    def test_deploy_simple_wsgi_app(self):
        instance_folder = path(sarge_cmd("new_instance '{}'"))

        put_json({'urlmap': [
                    {'type': 'wsgi',
                     'url': '/',
                     'app_factory': 'mytinyapp:gettheapp'},
                 ]},
                 instance_folder / 'sargeapp.yaml')
        app_py = ('def gettheapp(appcfg):\n'
                  '    def theapp(environ, start_response):\n'
                  '        start_response("200 OK", [])\n'
                  '        return ["hello sarge!\\n"]\n'
                  '    return theapp\n')
        put(StringIO(app_py), str(instance_folder / 'mytinyapp.py'))
        sarge_cmd("start_instance '%s'" % instance_folder.name)
        link_in_nginx(instance_folder.name)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge!\n")

    def test_deploy_new_instance(self):
        app_cfg = {
            'urlmap': [
                {'type': 'wsgi',
                 'url': '/',
                 'app_factory': 'mytinyapp:gettheapp'},
            ],
        }
        app_py_tmpl = ('def gettheapp(appcfg):\n'
                       '    def theapp(environ, start_response):\n'
                       '        start_response("200 OK", [])\n'
                       '        return ["hello sarge %s!\\n"]\n'
                       '    return theapp\n')

        # deploy instance one
        instance_folder_1 = path(sarge_cmd("new_instance '{}'"))
        put_json(app_cfg, instance_folder_1 / 'sargeapp.yaml')
        put(StringIO(app_py_tmpl % 'one'),
            str(instance_folder_1 / 'mytinyapp.py'))
        sarge_cmd("start_instance '%s'" % instance_folder_1.name)
        link_in_nginx(instance_folder_1.name)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge one!\n")

        # deploy instance two
        instance_folder_2 = path(sarge_cmd("new_instance '{}'"))
        put_json(app_cfg, instance_folder_2 / 'sargeapp.yaml')
        put(StringIO(app_py_tmpl % 'two'),
            str(instance_folder_2 / 'mytinyapp.py'))
        sarge_cmd("start_instance '%s'" % instance_folder_2.name)
        link_in_nginx(instance_folder_2.name)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge two!\n")

    def test_deploy_php(self):
        instance_folder = path(sarge_cmd("new_instance '{}'"))

        put_json({'urlmap': [
                    {'type': 'php', 'url': '/'},
                 ]},
                 instance_folder / 'sargeapp.yaml')

        app_php = ('<?php echo "hello from" . " PHP!\\n"; ?>')
        put(StringIO(app_php), str(instance_folder / 'someapp.php'))
        sarge_cmd("start_instance '%s'" % instance_folder.name)
        link_in_nginx(instance_folder.name)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/someapp.php'),
                         "hello from PHP!\n")

    def test_deploy_static_site(self):
        instance_folder = path(sarge_cmd("new_instance '{}'"))
        put_json({'urlmap': [
                    {'type': 'static', 'url': '/', 'path': ''},
                 ]},
                 instance_folder / 'sargeapp.yaml')

        with cd(str(instance_folder)):
            run("echo 'hello static!' > hello.html")
            run("mkdir sub")
            run("echo 'submarine' > sub/marine.txt")

        sarge_cmd("start_instance '%s'" % instance_folder.name)
        link_in_nginx(instance_folder.name)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/hello.html'),
                         "hello static!\n")

        self.assertEqual(get_url('http://192.168.13.13:8013/sub/marine.txt'),
                         "submarine\n")

    def test_start_server_using_default_executable_name(self):
        instance_folder = path(sarge_cmd("new_instance '{}'"))

        put_json({'urlmap': [
                    {'type': 'proxy',
                     'url': '/',
                     'upstream_url': 'http://localhost:43423'},
                 ]},
                 instance_folder / 'sargeapp.yaml')
        app_py = ('#!/usr/bin/env python\n'
                  'from wsgiref.simple_server import make_server\n'
                  'def theapp(environ, start_response):\n'
                  '    start_response("200 OK", [])\n'
                  '    return ["hello sarge!\\n"]\n'
                  'make_server("0", 43423, theapp).serve_forever()\n')
        put(StringIO(app_py), str(instance_folder / 'server'), mode=0755)
        sarge_cmd("start_instance '%s'" % instance_folder.name)
        link_in_nginx(instance_folder.name)
        sudo("service nginx reload")

        self.assertEqual(get_url('http://192.168.13.13:8013/'),
                         "hello sarge!\n")
