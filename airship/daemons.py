import os
import sys
import subprocess
from path import path


class SupervisorError(Exception):
    """ Something went wrong while talking to supervisord. """


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


# autorestart is disabled because otherwise it would keep restarting
# triggered buckets when they exit

SUPERVISORD_PROGRAM_TEMPLATE = """\
[program:%(name)s]
redirect_stderr = true
stdout_logfile = %(log)s
startsecs = %(startsecs)s
startretries = 1
autostart = %(autostart)s
autorestart = false
command = bin/sarge run %(bucket_id)s ./_run_process
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

    def _bucket_cfg(self, bucket_id):
        return self.config_dir / bucket_id

    def configure(self, home_path):
        with open(self.config_path, 'wb') as f:
            f.write(SUPERVISORD_CFG_TEMPLATE % {
                'home_path': home_path,
                'include_files': self.etc / 'supervisor.d' / '*',
            })

    def _configure_bucket(self, bucket, autostart):
        with self._bucket_cfg(bucket.id_).open('wb') as f:
            f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                'name': bucket.id_,
                'directory': bucket.folder,
                'run': bucket.run_folder,
                'log': bucket.log_path,
                'bucket_id': bucket.id_,
                'autostart': 'true' if autostart else 'false',
                'startsecs': 2 if autostart else 0,
            })

    def remove_bucket(self, bucket_id):
        self._bucket_cfg(bucket_id).unlink_p()
        try:
            self.ctl(['update'])
        except SupervisorError:
            pass  # maybe supervisord is stopped

    def ctl(self, cmd_args):
        if os.environ.get('SARGE_NO_SUPERVISORCTL'):
            return
        base_args = [self.ctl_path, '-c', self.config_path]
        try:
            return subprocess.check_call(base_args + cmd_args,
                                         stdout=sys.stderr)
        except subprocess.CalledProcessError:
            raise SupervisorError

    def configure_bucket_running(self, bucket):
        self._configure_bucket(bucket, True)
        self.ctl(['update'])

    def configure_bucket_stopped(self, bucket):
        self._configure_bucket(bucket, False)
        self.ctl(['update'])

    def trigger_bucket(self, bucket):
        self.ctl(['start', bucket.id_])
