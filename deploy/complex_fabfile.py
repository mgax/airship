from StringIO import StringIO
import json
from functools import wraps
from fabric.api import *
from fabric.contrib.files import exists
from fabric.contrib.console import confirm
from path import path
import imp

env['use_ssh_config'] = True


def create_deployer(name, deployment_env):

    deployer = imp.new_module('_sarge_deployer.{name}'.format(**locals()))
    deployer._deployment_env = deployment_env

    def module_func(func):
        setattr(deployer, func.__name__, func)
        return func

    deployer.module_func = module_func

    @deployer.module_func
    def module_task(func):
        @deployer.module_func
        @task
        @wraps(func)
        def wrapper(*args, **kwargs):
            with settings(**deployment_env):
                return func(*args, **kwargs)

        return wrapper

    @deployer.module_func
    def quote_json(config):
        return "'" + json.dumps(config).replace("'", "\\u0027") + "'"

    @deployer.module_func
    def _sarge_cmd(cmd):
        return "{sarge_home}/bin/sarge {cmd}".format(cmd=cmd, **env)

    @deployer.module_func
    def sarge(cmd):
        return run(deployer._sarge_cmd(cmd))

    @deployer.module_func
    def link_nginx(server_name=None):
        if server_name is None:
            server_name = env['sarge_nginx_instance'].format(**env)

        quoted_config = deployer.quote_json(deployer.nginx_config())
        run('sudo tek-nginx configure {server_name}:80 {quoted_config}'
            .format(**locals()))

        return server_name

    @deployer.module_func
    def unlink_nginx():
        server_name = env['sarge_nginx_instance'].format(**env)
        run('sudo tek-nginx delete -f {server_name}:80'.format(**locals()))

    @deployer.module_func
    def instances():
        name = env['sarge_application_name']
        for instance in json.loads(deployer.sarge('list'))['instances']:
            if instance['meta']['APPLICATION_NAME'] != name:
                continue
            yield instance

    @deployer.module_task
    def destroy_instance(sarge_instance):
        with settings(sarge_instance=sarge_instance):
            deployer.unlink_nginx()
            deployer.sarge("destroy {sarge_instance}".format(**env))

    @deployer.module_task
    def destroy_all():
        for instance in deployer.instances():
            deployer.destroy_instance(instance['id'])

    @deployer.module_task
    def shell(sarge_instance=None):
        if sarge_instance is None:
            sarge_instance = list(deployer.instances())[0]['id']
        open_shell("exec " + deployer._sarge_cmd("run " + sarge_instance))

    @deployer.module_task
    def supervisorctl():
        open_shell("exec {sarge_home}/bin/supervisorctl".format(**env))

    return deployer


def create_web_deployer(name, extra_env):

    deployer = create_deployer(name, extra_env)

    @deployer.module_task
    def virtualenv():
        if not exists(env['gardensale_venv']):
            run("virtualenv '{gardensale_venv}' "
                "--distribute --no-site-packages "
                "-p '{gardensale_python_bin}'"
                .format(**env))

        put("requirements.txt", str(env['gardensale_venv']))
        run("{gardensale_venv}/bin/pip install "
            "-r {gardensale_venv}/requirements.txt"
            .format(**env))

    @deployer.module_func
    def nginx_config():
        instance_dir = env['sarge_home'] / env['sarge_instance']
        return {
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
                 'path': instance_dir / 'gardensale' / 'static'},
            ],
        }

    @deployer.module_func
    def install():
        instance_dir = env['sarge_home'] / env['sarge_instance']
        if not exists(instance_dir / '.git'):
            run("git init '{instance_dir}'"
                .format(instance_dir=instance_dir))
        local("git push -f '{host_string}:{instance_dir}' "
              "HEAD:refs/heads/incoming"
              .format(instance_dir=instance_dir, **env))
        with cd(instance_dir):
            run("git reset incoming --hard")

        sarge_rc = (
            "source {gardensale_venv}/bin/activate\n"
        ).format(**env)
        put(StringIO(sarge_rc), str(instance_dir / 'sarge_rc.sh'))

        put(StringIO("#!/bin/bash\n"
                     "exec python manage.py fcgi -s fcgi.sock\n"
                     .format(**env)),
            str(instance_dir / 'server'),
            mode=0755)

    @deployer.module_task
    def deploy():
        instance_config = {
            'application_name': env['sarge_application_name'],
        }
        instance_config.update(env.get('sarge_instance_config', {}))
        out = deployer.sarge("new " + deployer.quote_json(instance_config))
        sarge_instance = out.strip()
        with settings(sarge_instance=sarge_instance):
            deployer.install()
            deployer.sarge("start {sarge_instance}".format(**env))
            url = 'http://' + deployer.link_nginx()
            if confirm("Deployed at {url} - make it live?".format(**locals())):
                deployer.link_nginx(env['sarge_nginx_live'])
                for other_instance in deployer.instances():
                    if other_instance['id'] == env['sarge_instance']:
                        continue
                    deployer.destroy_instance(other_instance['id'])
            else:
                if confirm("Destroy instance {sarge_instance}?".format(**env)):
                    deployer.destroy_instance(env['sarge_instance'])

    return deployer


def create_worker_deployer(name, extra_env):

    deployer = create_deployer(name, extra_env)

    @deployer.module_func
    def install():
        instance_dir = env['sarge_home'] / env['sarge_instance']
        if not exists(instance_dir / '.git'):
            run("git init '{instance_dir}'"
                .format(instance_dir=instance_dir))
        local("git push -f '{host_string}:{instance_dir}' "
              "HEAD:refs/heads/incoming"
              .format(instance_dir=instance_dir, **env))
        with cd(instance_dir):
            run("git reset incoming --hard")

        sarge_rc = (
            "source {gardensale_venv}/bin/activate\n"
        ).format(**env)
        put(StringIO(sarge_rc), str(instance_dir / 'sarge_rc.sh'))

        put(StringIO("#!/bin/bash\n"
                     "exec celery worker --app=gardensale.worker -l info\n"
                     .format(**env)),
            str(instance_dir / 'server'),
            mode=0755)

    @deployer.module_task
    @warn_if_branch_is_not_sync
    @warn_if_live
    def deploy():
        for other_instance in deployer.instances():
            deployer.sarge("destroy " + other_instance['id'])
        instance_config = {
            'application_name': env['sarge_application_name'],
        }
        instance_config.update(env.get('sarge_instance_config', {}))
        out = deployer.sarge("new " + deployer.quote_json(instance_config))
        sarge_instance = out.strip()
        with settings(sarge_instance=sarge_instance):
            deployer.install()
            deployer.sarge("start {sarge_instance}".format(**env))

    return deployer


_staging_home = path('/var/local/gardensale-staging')
staging = create_web_deployer('staging', {
        'host_string': 'app@gardensale.example.com',
        'gardensale_python_bin': '/usr/local/Python-2.7.3/bin/python',
        'sarge_application_name': 'web',
        'sarge_nginx_instance': "staging-{sarge_instance}.gardensale.example.com",
        'sarge_nginx_live': "staging.gardensale.example.com",
        'sarge_instance_config': {'prerun': 'sarge_rc.sh'},
        'sarge_home':      _staging_home,
        'gardensale_venv': _staging_home / 'var' / 'gardensale-venv',
    })


staging_worker = create_worker_deployer('staging_worker', {
        'host_string': 'app@gardensale.example.com',
        'gardensale_python_bin': '/usr/local/Python-2.7.3/bin/python',
        'sarge_application_name': 'worker',
        'sarge_instance_config': {'prerun': 'sarge_rc.sh'},
        'sarge_home':      _staging_home,
        'gardensale_venv': _staging_home / 'var' / 'gardensale-venv',
    })
del staging_worker.supervisorctl
del staging_worker.destroy_instance
del staging_worker.destroy_all


_production_home = path('/var/local/gardensale-production')
production = create_web_deployer('production', {
        'host_string': 'app@gardensale.example.com',
        'gardensale_python_bin': '/usr/local/Python-2.7.3/bin/python',
        'sarge_application_name': 'web',
        'sarge_nginx_instance': "{sarge_instance}.gardensale.example.com",
        'sarge_nginx_live': "gardensale.example.com",
        'sarge_instance_config': {'prerun': 'sarge_rc.sh'},
        'sarge_home':      _production_home,
        'gardensale_venv': _production_home / 'var' / 'gardensale-venv',
        'gardensale_is_production': True,
    })


production_worker = create_worker_deployer('production_worker', {
        'host_string': 'app@gardensale.example.com',
        'gardensale_python_bin': '/usr/local/Python-2.7.3/bin/python',
        'sarge_application_name': 'worker',
        'sarge_instance_config': {'prerun': 'sarge_rc.sh'},
        'sarge_home':      _staging_home,
        'gardensale_venv': _staging_home / 'var' / 'gardensale-venv',
    })
del production_worker.supervisorctl
del production_worker.destroy_instance
del production_worker.destroy_all
