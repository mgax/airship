import sys
import subprocess
from path import path


SUPERVISORD_CFG_TEMPLATE = """\
[unix_http_server]
file = %(home_path)s/var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = \
supervisor.rpcinterface:make_main_rpcinterface

[supervisord]
logfile = %(home_path)s/var/log/supervisor.log
pidfile = %(home_path)s/var/run/supervisor.pid
directory = %(home_path)s

[supervisorctl]
serverurl = unix://%(home_path)s/var/run/supervisor.sock

[include]
files = %(include_files)s
"""


SUPERVISORD_PROGRAM_TEMPLATE = """\
[program:%(name)s]
directory = %(directory)s
redirect_stderr = true
stdout_logfile = %(log)s
startsecs = 2
startretries = 1
autostart = %(autostart)s
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

    def _instance_cfg(self, instance_id):
        return self.config_dir / instance_id

    def configure(self, home_path):
        with open(self.config_path, 'wb') as f:
            f.write(SUPERVISORD_CFG_TEMPLATE % {
                'home_path': home_path,
                'include_files': self.etc / 'supervisor.d' / '*',
            })

    def _configure_instance(self, instance, autostart):
        with self._instance_cfg(instance.id_).open('wb') as f:
            f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                'name': instance.id_,
                'directory': instance.folder,
                'run': instance.run_folder,
                'log': instance.log_path,
                'environment': 'SARGEAPP_CFG="%s"' % instance.appcfg_path,
                'command': instance.folder / 'server',
                'autostart': 'true' if autostart else 'false',
            })

    def remove_instance(self, instance_id):
        self._instance_cfg(instance_id).unlink_p()

    def ctl(self, cmd_args):
        base_args = [self.ctl_path, '-c', self.config_path]
        return subprocess.check_call(base_args + cmd_args)

    def restart_instance(self, name):
        self.ctl(['restart', name])

    def start_instance(self, instance):
        self._configure_instance(instance, True)
        self.ctl(['update'])

    def stop_instance(self, instance):
        self._configure_instance(instance, False)
        self.ctl(['update'])

    def print_status(self):
        self.ctl(['status'])
