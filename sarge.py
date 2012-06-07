import json


DEPLOYMENT_CFG = 'deployments.yaml'
SUPERVISORD_CFG = 'supervisord.conf'

SUPERVISORD_CFG_TEMPLATE = """\
[unix_http_server]
file = %(home_path)s/supervisord.sock
%(extra_server_stuff)s

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

    def new_version(self):
        version_folder = self.folder/'1'
        version_folder.makedirs()
        return version_folder


class Sarge(object):

    def __init__(self, home_path):
        self.home_path = home_path
        self.deployments = []
        self._configure()

    def _configure(self):
        with open(self.home_path/DEPLOYMENT_CFG, 'rb') as f:
            config = json.load(f)
            for deployment_config in config.pop('deployments'):
                depl = Deployment()
                depl.name = deployment_config['name']
                depl.config = deployment_config
                depl.folder = self.home_path/depl.name
                self.deployments.append(depl)
            self.config = config

    def generate_supervisord_configuration(self):
        with open(self.home_path/SUPERVISORD_CFG, 'wb') as f:
            extra_server_stuff = ""
            sock_owner = self.config.get('supervisord_socket_owner')
            if sock_owner is not None:
                extra_server_stuff += "chown = %s\n" % sock_owner

            f.write(SUPERVISORD_CFG_TEMPLATE % {
                'home_path': self.home_path,
                'extra_server_stuff': extra_server_stuff,
            })
            for depl in self.deployments:
                f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                    'name': depl.name,
                    'command': depl.config['command'],
                })

    def get_deployment(self, name):
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError
