import sys
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


QUICK_WSGI_APP_TEMPLATE = """\
from flup.server.fcgi import WSGIServer
from importlib import import_module
app = getattr(import_module(%(module_name)r), %(attribute_name)r)
server = WSGIServer(app, bindAddress=%(socket_path)r, umask=0)
server.run()
"""


class Deployment(object):

    active_version_folder = None

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
        if 'tmp-wsgi-app' in self.config:
            app_import_name = self.config['tmp-wsgi-app']
            with open(version_folder/'quickapp.py', 'wb') as f:
                module_name, attribute_name = app_import_name.split(':')
                f.write(QUICK_WSGI_APP_TEMPLATE % {
                    'module_name': module_name,
                    'attribute_name': attribute_name,
                    'socket_path': str(version_folder/'sock.fcgi'),
                })
            self.config['command'] = "%s quickapp.py" % sys.executable
        self.sarge.generate_supervisord_configuration()
        self.sarge.supervisorctl(['reread'])

    def start(self):
        self.sarge.supervisorctl(['start', self.name])

    def stop(self):
        self.sarge.supervisorctl(['stop', self.name])


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
                version_folder = depl.active_version_folder
                if version_folder is None:
                    continue
                f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                    'name': depl.name,
                    'command': depl.config['command'],
                    'directory': version_folder,
                })

    def get_deployment(self, name):
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError

    def supervisorctl(self, cmd_args):
        raise NotImplementedError


def init_cmd(sarge, args):
    sarge.generate_supervisord_configuration()


def new_version_cmd(sarge, args):
    print sarge.get_deployment(args.name).new_version()


def stop_cmd(sarge, args):
    sarge.get_deployment(args.name).stop()


def start_cmd(sarge, args):
    sarge.get_deployment(args.name).start()


def build_args_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sarge_home')
    subparsers = parser.add_subparsers()
    init = subparsers.add_parser('init')
    init.set_defaults(func=init_cmd)
    new_version = subparsers.add_parser('new_version')
    new_version.set_defaults(func=new_version_cmd)
    new_version.add_argument('name')
    start = subparsers.add_parser('start')
    start.set_defaults(func=start_cmd)
    start.add_argument('name')
    stop = subparsers.add_parser('stop')
    stop.set_defaults(func=stop_cmd)
    stop.add_argument('name')
    return parser


def main(raw_arguments):
    from path import path
    parser = build_args_parser()
    args = parser.parse_args(raw_arguments)
    sarge = Sarge(path(args.sarge_home))
    args.func(sarge, args)


if __name__ == '__main__':
    main(sys.argv[1:])
