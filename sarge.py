import json


DEPLOYMENT_CFG = 'deployments.yaml'
SUPERVISORD_CFG = 'supervisord.conf'

SUPERVISORD_CFG_TEMPLATE = """\
[unix_http_server]
file = %(home_path)s/supervisord.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisord]
logfile = %(home_path)s/supervisord.log
pidfile = %(home_path)s/supervisord.pid
directory = %(home_path)s

[supervisorctl]
serverurl = unix://%(home_path)s/supervisord.sock
"""

SUPERVISORD_PROGRAM_TEMPLATE = """\
[program:%(name)s]
command = %(command)s
redirect_stderr = true
startsecs = 2
"""


class Deployment(object):
    pass


class Sarge(object):

    def __init__(self, home_path):
        self.home_path = home_path
        self.deployments = []
        self._configure()

    def _configure(self):
        with open(self.home_path/DEPLOYMENT_CFG, 'rb') as f:
            for deployment_config in json.load(f)['deployments']:
                depl = Deployment()
                depl.name = deployment_config['name']
                depl.config = deployment_config
                self.deployments.append(depl)

    def generate_supervisord_configuration(self):
        with open(self.home_path/SUPERVISORD_CFG, 'wb') as f:
            f.write(SUPERVISORD_CFG_TEMPLATE % {'home_path': self.home_path})
            for depl in self.deployments:
                f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                    'name': depl.name,
                    'command': depl.config['command'],
                })
