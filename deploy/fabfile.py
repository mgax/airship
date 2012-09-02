from StringIO import StringIO
import json
from fabric.api import *
from path import path


env['sarge_home'] = '/var/local/sarge_demo'
env['python_bin'] = 'python'


DEMO_APP_TEMPLATE = """\
#!/usr/bin/env python
from wsgiref.simple_server import make_server, demo_app
httpd = make_server("0.0.0.0", 8000, demo_app)
httpd.serve_forever()
"""


def sarge(cmd):
    return run("{sarge_home}/bin/sarge {cmd}".format(cmd=cmd, **env))


def quote_json(config):
    return "'" + json.dumps(config).replace("'", "\\u0027") + "'"


@task
def bootstrap():
    username = run("whoami")
    sudo("mkdir -p {sarge_home}".format(**env))
    sudo("chown {username}: {sarge_home}".format(username=username, **env))
    put("bootstrap-sarge.py", str(env['sarge_home']))
    with cd(env['sarge_home']):
        run("curl -O 'https://raw.github.com/jaraco/path.py/2.3/path.py'")
        run("{python_bin} bootstrap-sarge.py".format(**env))
        run("bin/supervisord")


@task
def install(instance_id):
    put(StringIO(DEMO_APP_TEMPLATE.format(**env)),
        str(path(env['sarge_home']) / instance_id / 'server'),
        mode=0755)


@task
def clean_old(name):
    for instance in json.loads(sarge('list'))['instances']:
        if instance['meta']['APPLICATION_NAME'] != name:
            continue
        sarge("stop " + instance['id'])
        sarge("destroy " + instance['id'])


@task
def deploy(name='demo_app'):
    execute('clean_old', name)
    instance_config = {'application_name': name}
    instance_id = sarge("new " + quote_json(instance_config))
    execute('install', instance_id)
    sarge("start '%s'" % instance_id)
