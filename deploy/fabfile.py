from fabric.api import *
from path import path


env['sarge_home'] = '/var/local/sarge_demo'
env['python_bin'] = 'python'


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
