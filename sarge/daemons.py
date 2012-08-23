import sys
from path import path


class Supervisor(object):
    """ Wrapper for supervisor configuration and control """

    ctl_path = str(path(sys.prefix).abspath() / 'bin' / 'supervisorctl')

    def __init__(self, config_path):
        self.config_path = config_path

    def ctl(self, cmd_args):
        from .core import subprocess
        base_args = [self.ctl_path, '-c', self.config_path]
        return subprocess.check_call(base_args + cmd_args)
