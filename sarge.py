import sys
import json
import subprocess
from path import path


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

SUPERVISORD_PROGRAM_TEMPLATE = """
[program:%(name)s]
directory = %(directory)s
redirect_stderr = true
stdout_logfile = %(directory)s/stdout.log
startsecs = 2
%(extra_program_stuff)s
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
        self.generate_nginx_configuration()
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
        self.sarge.supervisorctl(['restart', self.name])

    def generate_nginx_configuration(self):
        version_folder = self.active_version_folder

        app_config_path = version_folder/'sargeapp.yaml'
        if app_config_path.exists():
            with open(app_config_path, 'rb') as f:
                app_config = json.load(f)
        else:
            app_config = {}

        with open(version_folder/'nginx-site.conf', 'wb') as f:
            f.write("server {\n")

            nginx_options = app_config.get('nginx_options', {})
            for key, value in sorted(nginx_options.items()):
                f.write("  %s: %s;\n" % (key, value))

            for entry in app_config.get('urlmap', []):
                if entry['type'] == 'static':
                    f.write("location %(url)s {\n"
                            "    alias %(version_folder)s/%(path)s;\n"
                            "}\n" % dict(entry, version_folder=version_folder))
                elif entry['type'] == 'wsgi':
                    socket_path = version_folder/'wsgi-app.sock'
                    f.write("location %(url)s {\n"
                            "    include /etc/nginx/fastcgi_params;\n"
                            "    fastcgi_param PATH_INFO $fastcgi_script_name;\n"
                            "    fastcgi_param SCRIPT_NAME "";\n"
                            "    fastcgi_pass unix:%(socket_path)s;\n"
                            "}\n" % dict(entry, socket_path=socket_path))
                    self.config['tmp-wsgi-app'] = entry['wsgi_app']

                elif entry['type'] == 'php':
                    socket_path = version_folder/'php.sock'
                    f.write("location %(url)s {\n"
                            "    include /etc/nginx/fastcgi_params;\n"
                            "    fastcgi_param SCRIPT_FILENAME "
                                    "%(version_folder)s$fastcgi_script_name;\n"
                            "    fastcgi_param PATH_INFO $fastcgi_script_name;\n"
                            "    fastcgi_param SCRIPT_NAME "";\n"
                            "    fastcgi_pass unix:%(socket_path)s;\n"
                            "}\n" % dict(entry,
                                         socket_path=socket_path,
                                         version_folder=version_folder))

                    self.config['command'] = (
                        "/usr/bin/spawn-fcgi -s %(socket_path)s "
                        "-f /usr/bin/php5-cgi -n"
                        % {'socket_path': socket_path})

                else:
                    raise NotImplementedError

            f.write("}\n")

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
                extra_program_stuff = ""
                if depl.config.get('autorestart', None) == 'always':
                    extra_program_stuff = "autorestart = true\n"
                command = depl.config.get('command')
                if command is not None:
                    extra_program_stuff = "command = %s\n" % command
                f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                    'name': depl.name,
                    'directory': version_folder,
                    'extra_program_stuff': extra_program_stuff,
                })

    def get_deployment(self, name):
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError

    def supervisorctl(self, cmd_args):
        subprocess.check_call
        base_args = ['supervisorctl', '-c', self.home_path/SUPERVISORD_CFG]
        return subprocess.check_call(base_args + cmd_args)

    def status(self):
        self.supervisorctl(['status'])


def init_cmd(sarge, args):
    sarge.generate_supervisord_configuration()


def status_cmd(sarge, args):
    sarge.status()


def activate_version_cmd(sarge, args):
    version_folder = path(args.version_folder).abspath()
    sarge.get_deployment(args.name).activate_version(version_folder)


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
    init_parser = subparsers.add_parser('init')
    init_parser.set_defaults(func=init_cmd)
    status_parser = subparsers.add_parser('status')
    status_parser.set_defaults(func=status_cmd)
    new_version_parser = subparsers.add_parser('new_version')
    new_version_parser.set_defaults(func=new_version_cmd)
    new_version_parser.add_argument('name')
    activate_version_parser = subparsers.add_parser('activate_version')
    activate_version_parser.set_defaults(func=activate_version_cmd)
    activate_version_parser.add_argument('name')
    activate_version_parser.add_argument('version_folder')
    start_parser = subparsers.add_parser('start')
    start_parser.set_defaults(func=start_cmd)
    start_parser.add_argument('name')
    stop_parser = subparsers.add_parser('stop')
    stop_parser.set_defaults(func=stop_cmd)
    stop_parser.add_argument('name')
    return parser


def main(raw_arguments):
    parser = build_args_parser()
    args = parser.parse_args(raw_arguments)
    sarge = Sarge(path(args.sarge_home).abspath())
    args.func(sarge, args)


if __name__ == '__main__':
    main(sys.argv[1:])
