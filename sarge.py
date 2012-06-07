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
directory = %(directory)s
command = %(command)s
redirect_stderr = true
startsecs = 2
"""


class Deployment(object):

    @property
    def folder(self):
        return self.sarge.home_path/self.name

    def new_version(self):
        # TODO make sure we don't reuse version IDs. we probably need to
        # save the counter to a file in `self.folder`.
        import itertools
        for c in itertools.count(1):
            version_folder = self.folder/str(c)
            if not version_folder.exists():
                version_folder.makedirs()
                return version_folder

    def activate_version(self, version_folder):
        self.active_version_folder = version_folder # TODO persist on disk
        self.sarge.generate_supervisord_configuration()
        self.sarge.supervisorctl(['reread'])

    def start(self):
        self.sarge.supervisorctl(['start', self.name])


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
                depl.sarge = self
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
                    'directory': depl.active_version_folder,
                })

    def get_deployment(self, name):
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError

    def supervisorctl(self, cmd_args):
        raise NotImplementedError
