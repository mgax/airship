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


class Supervisor(object):
    """ Wrapper for supervisor configuration and control """

    ctl_path = str(path(sys.prefix).abspath() / 'bin' / 'supervisorctl')

    def __init__(self, config_path):
        self.config_path = config_path

    def configure(self, home_path, include_files):
        with open(self.config_path, 'wb') as f:
            f.write(SUPERVISORD_CFG_TEMPLATE % {
                'home_path': home_path,
                'include_files': include_files,
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
