import sys
import subprocess
from path import path


SUPERVISORD_CFG_TEMPLATE = """\
[unix_http_server]
file = %(home_path)s/supervisord.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = \
supervisor.rpcinterface:make_main_rpcinterface

[supervisord]
logfile = %(home_path)s/supervisord.log
pidfile = %(home_path)s/supervisord.pid
directory = %(home_path)s

[supervisorctl]
serverurl = unix://%(home_path)s/supervisord.sock

[include]
files = %(include_files)s
"""


SUPERVISORD_PROGRAM_TEMPLATE = """\
[program:%(name)s]
directory = %(directory)s
redirect_stderr = true
stdout_logfile = %(run)s/stdout.log
startsecs = 2
autostart = false
environment = %(environment)s
command = %(command)s
"""


class Supervisor(object):
    """ Wrapper for supervisor configuration and control """

    ctl_path = str(path(sys.prefix).abspath() / 'bin' / 'supervisorctl')

    def __init__(self, etc):
        self.etc = etc
        self.config_dir.makedirs_p()

    @property
    def config_path(self):
        return self.etc / 'supervisor.conf'

    @property
    def config_dir(self):
        return self.etc / 'supervisor.d'

    def configure(self, home_path):
        with open(self.config_path, 'wb') as f:
            f.write(SUPERVISORD_CFG_TEMPLATE % {
                'home_path': home_path,
                'include_files': self.etc / 'supervisor.d' / '*',
            })

    def configure_deployment(self, instance_id, programs):
        with open(self.config_dir / instance_id, 'wb') as f:
            for name, cfg in programs:
                f.write(SUPERVISORD_PROGRAM_TEMPLATE % cfg)

            f.write("[group:%(name)s]\nprograms = %(programs)s\n" % {
                'name': instance_id,
                'programs': ','.join(name for name, cfg in programs),
            })

    def ctl(self, cmd_args):
        base_args = [self.ctl_path, '-c', self.config_path]
        return subprocess.check_call(base_args + cmd_args)

    def update(self):
        self.ctl(['update'])

    def restart_deployment(self, name):
        self.ctl(['restart', name + ':*'])

    def start_deployment(self, name):
        self.ctl(['start', name + ':*'])

    def stop_deployment(self, name):
        self.ctl(['stop', name + ':*'])

    def print_status(self):
        self.ctl(['status'])
