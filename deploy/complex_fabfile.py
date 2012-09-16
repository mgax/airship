from StringIO import StringIO
import subprocess
import json
from functools import wraps
from fabric.api import *
from fabric.contrib.files import exists
from fabric.contrib.console import confirm
from path import path
import imp


def create_sarge_deployer(name, deployer_env):
    from blinker import Namespace
    from blinker.base import symbol

    deployer = imp.new_module('_sarge_deployer.{name}'.format(**locals()))
    deployer.env = deployer_env
    deployer.app_options = {}
    deployer.default_app = None
    deployer.signal_ns = Namespace()
    deployer.install = deployer.signal_ns.signal('install')
    deployer.has_started = deployer.signal_ns.signal('has_started')
    deployer.promote = deployer.signal_ns.signal('promote')
    deployer.will_stop = deployer.signal_ns.signal('will_stop')

    def _func(func):
        setattr(deployer, func.__name__, func)
        return func

    deployer._func = _func

    @deployer._func
    def _task(func):
        @deployer._func
        @task
        @wraps(func)
        def wrapper(*args, **kwargs):
            with settings(**deployer.env):
                return func(*args, **kwargs)

        return wrapper

    @deployer._func
    def quote_json(config):
        return "'" + json.dumps(config).replace("'", "\\u0027") + "'"

    @deployer._func
    def on(signal_name, app_name='ANY'):
        signal = deployer.signal_ns[signal_name]
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func()
            signal.connect(wrapper, symbol(app_name), False)
            return func
        return decorator

    @deployer._func
    def add_application(app_name, **options):
        if deployer.default_app is None:
            deployer.default_app = app_name
        deployer.app_options[app_name] = options

    def _sarge_cmd(cmd):
        return "{sarge_home}/bin/sarge {cmd}".format(cmd=cmd, **env)

    def _sarge(cmd):
        return run(_sarge_cmd(cmd))

    def _new():
        instance_config = {
            'application_name': env['deployer_app_name'],
        }
        instance_config.update(env.get('sarge_instance_config', {}))
        out = _sarge("new " + deployer.quote_json(instance_config))
        sarge_instance = out.strip()
        return sarge_instance

    def _destroy_instance(sarge_instance):
        with settings(sarge_instance=sarge_instance):
            deployer.will_stop.send(symbol(env['deployer_app_name']))
            _sarge("destroy {sarge_instance}".format(**env))

    def _remove_instances(keep=None):
        for other_instance in _instances():
            if other_instance['id'] == keep:
                continue
            with settings(sarge_instance=other_instance['id']):
                app_name = other_instance['meta']['APPLICATION_NAME']
                deployer.will_stop.send(symbol(app_name))
                _destroy_instance(other_instance['id'])

    def _rolling_deploy():
        sarge_instance = _new()
        instance_dir = env['sarge_home'] / sarge_instance
        with settings(sarge_instance=sarge_instance,
                      instance_dir=instance_dir):
            deployer.install.send(symbol(env['deployer_app_name']))
            _sarge("start {sarge_instance}".format(**env))
            deployer.has_started.send(symbol(env['deployer_app_name']))
            if confirm("Deployed {sarge_instance} - make it live?"
                       .format(**locals())):
                deployer.promote.send(symbol(env['deployer_app_name']))
                _remove_instances(keep=env['sarge_instance'])
            else:
                if confirm("Destroy instance {sarge_instance}?".format(**env)):
                    deployer.will_stop.send(symbol(env['deployer_app_name']))
                    _destroy_instance(env['sarge_instance'])

    def _simple_deploy():
        _remove_instances()
        sarge_instance = _new()
        instance_dir = env['sarge_home'] / sarge_instance
        with settings(sarge_instance=sarge_instance,
                      instance_dir=instance_dir):
            deployer.install.send(symbol(env['deployer_app_name']))
            _sarge("start {sarge_instance}".format(**env))
            deployer.has_started.send(symbol(env['deployer_app_name']))
            deployer.promote.send(symbol(env['deployer_app_name']))

    def _instances():
        app_name = env['deployer_app_name']
        for instance in json.loads(_sarge('list'))['instances']:
            if instance['meta']['APPLICATION_NAME'] != app_name:
                continue
            yield instance

    @deployer._task
    def deploy(app_name=None):
        if app_name is None:
            print "Available applications: %r" % deployer.app_options.keys()
            return
        with settings(deployer_app_name=app_name):
            if deployer.app_options[app_name].get('rolling_update', False):
                _rolling_deploy()
            else:
                _simple_deploy()

    @deployer._task
    def shell(sarge_instance=None):
        if sarge_instance is None:
            sarge_instance = deployer.default_app
        open_shell("exec " + _sarge_cmd("run " + sarge_instance))

    @deployer._task
    def supervisorctl():
        open_shell("exec {sarge_home}/bin/supervisorctl".format(**env))

    return deployer


env['use_ssh_config'] = True

SENTRY_DSN = ('http://5163c01deaf54c2a814c71a2a214a241'
                    ':2eedc02b46840f36ae9e284da09636f5'
                    '@sentry.machine.example.com/9')

SARGE_HOME = path('/var/local/testy')


testy = create_sarge_deployer('testy', {
        'host_string': 'machine.example.com',
        'testy_python_bin': '/usr/local/Python-2.7.3/bin/python',
        'sarge_instance_config': {'prerun': 'sarge_rc.sh'},
        'sarge_home': SARGE_HOME,
        'testy_venv': SARGE_HOME / 'var' / 'testy-venv',
        'testy_redis_var': SARGE_HOME / 'var' / 'testy-redis',
        'testy_bin': SARGE_HOME / 'var' / 'testy-bin',
        'sentry_dsn': SENTRY_DSN,
        'cube_collector': 'http://localhost:1080',
        'testy_redis_var': SARGE_HOME / 'var' / 'testy-redis',
        'testy_node_modules': SARGE_HOME / 'var' / 'testy-node',
        'testy_nginx_instance': "testy-{sarge_instance}.machine.example.com",
        'testy_nginx_live': "testy.machine.example.com",
    })

testy.add_application('web', rolling_update=True)
testy.add_application('worker')
testy.add_application('redis')
testy.add_application('cubecol')
testy.add_application('cubeval')

_testy_env = testy.env

_quote_json = testy.quote_json


@task
def virtualenv():
    with settings(**_testy_env):
        if not exists(env['testy_venv']):
            run("virtualenv '{testy_venv}' "
                "--distribute --no-site-packages "
                "-p '{testy_python_bin}'"
                .format(**env))

        put("requirements.txt", str(env['testy_venv']))
        run("{testy_venv}/bin/pip install "
            "-r {testy_venv}/requirements.txt"
            .format(**env))


@task
def npm():
    with settings(**_testy_env):
        run("mkdir -p {testy_node_modules}".format(**env))
        with cd(env['testy_node_modules']):
            run("npm install cube")


@testy.on('install', 'web')
@testy.on('install', 'worker')
def install_flask_app():
    src = subprocess.check_output(['git', 'archive', 'HEAD'])
    put(StringIO(src), str(env['instance_dir'] / '_src.tar'))
    with cd(env['instance_dir']):
        try:
            run("tar xvf _src.tar")
        finally:
            run("rm _src.tar")

    run("mkdir {instance_dir}/instance".format(**env))

    sarge_rc = (
        "source {testy_venv}/bin/activate\n"
        "export REDIS_SOCKET={testy_redis_var}/redis.sock\n"
        "export SENTRY_DSN={sentry_dsn}\n"
        "export CUBE_COLLECTOR={cube_collector}\n"
    ).format(**env)
    put(StringIO(sarge_rc), str(env['instance_dir'] / 'sarge_rc.sh'))

    app_name = env['deployer_app_name']

    if app_name == 'web':
        put(StringIO("#!/bin/bash\n"
                     "exec python manage.py runfcgi -s fcgi.sock\n"
                     .format(**env)),
            str(env['instance_dir'] / 'server'),
            mode=0755)

    elif app_name == 'worker':
        put(StringIO("#!/bin/bash\n"
                     "exec celery worker --app=work.celery --loglevel=INFO\n"
                     .format(**env)),
            str(env['instance_dir'] / 'server'),
            mode=0755)


@testy.on('has_started', 'web')
def link_nginx(server_name=None):
    if server_name is None:
        server_name = env['testy_nginx_instance'].format(**env)

    instance_dir = env['sarge_home'] / env['sarge_instance']

    nginx_config = {
        'options': {
            'send_timeout': '2m',
            'client_max_body_size': '20m',
            'proxy_buffers': '8 16k',
            'proxy_buffer_size': '32k',
        },
        'urlmap': [
            {'type': 'fcgi', 'url': '/',
             'socket': 'unix:' + instance_dir / 'fcgi.sock'},
            {'type': 'static', 'url': '/static',
             'path': instance_dir / 'testy' / 'static'},
        ],
    }

    quoted_config = _quote_json(nginx_config)
    run('sudo tek-nginx configure {server_name}:80 {quoted_config}'
        .format(**locals()))

    print "nginx: {server_name}".format(**locals())


@testy.on('promote', 'web')
def link_nginx_live():
    link_nginx(server_name=env['testy_nginx_live'])


@testy.on('will_stop', 'web')
def unlink_nginx():
    server_name = env['testy_nginx_instance'].format(**env)
    run('sudo tek-nginx delete -f {server_name}:80'.format(**locals()))


@testy.on('install', 'redis')
def install_redis():
    run("mkdir -p {testy_redis_var}".format(**env))
    put(StringIO("daemonize no\n"
                 "port 0\n"
                 "unixsocket {testy_redis_var}/redis.sock\n"
                 "dir {testy_redis_var}\n"
                 "loglevel notice\n"
                 "appendonly yes\n"
                 "appendfsync always\n"
                 .format(**env)),
        str(env['instance_dir'] / 'redis.conf'))

    put(StringIO("#!/bin/bash\n"
                 "exec redis-server redis.conf\n"
                 .format(**env)),
        str(env['instance_dir'] / 'server'),
        mode=0755)


@testy.on('install', 'cubeval')
def install_cubeval():
    put(StringIO("#!/bin/bash\n"
                 "cd {testy_node_modules}/node_modules/cube\n"
                 "exec node bin/evaluator.js\n"
                 .format(**env)),
        str(env['instance_dir'] / 'server'),
        mode=0755)


@testy.on('install', 'worker')
def install_worker_cronjob():
    put(StringIO("#!/usr/bin/env python\n"
                 "import work\n"
                 "work.download_page.delay()\n"
                 .format(**env)),
        str(env['instance_dir'] / 'cronjob'),
        mode=0755)

    run("mkdir -p {testy_bin}".format(**env))
    put(StringIO("#!/bin/bash\n"
                 "{sarge_home}/bin/sarge run {sarge_instance} ./cronjob\n"
                 .format(**env)),
        str(env['testy_bin'] / 'worker-cron'),
        mode=0755)


@testy.on('install', 'cubecol')
def install():
    cube_bin = env['testy_node_modules'] / 'node_modules' / 'cube' / 'bin'
    put(StringIO("#!/bin/bash\n"
                 "exec node {cube_bin}/collector.js\n"
                 .format(cube_bin=cube_bin, **env)),
        str(env['instance_dir'] / 'server'),
        mode=0755)


# remap tasks to top-level namespace
deploy = testy.deploy
supervisorctl = testy.supervisorctl
shell = testy.shell
del testy
