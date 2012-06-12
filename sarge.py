import sys
import json
import subprocess
from importlib import import_module
from path import path
import blinker


DEPLOYMENT_CFG = 'deployments.yaml'
DEPLOYMENT_CFG_DIR = 'deployments'
SUPERVISORD_CFG = 'supervisord.conf'
SUPERVISOR_DEPLOY_CFG = 'supervisor_deploy.conf'
RUN_FOLDER = 'run'

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

[include]
files = """ + path(RUN_FOLDER)/'*'/SUPERVISOR_DEPLOY_CFG + """
"""

SUPERVISORD_PROGRAM_TEMPLATE = """
[program:%(name)s]
directory = %(directory)s
redirect_stderr = true
stdout_logfile = %(run)s/stdout.log
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

supervisorctl_path = str(path(sys.prefix).abspath()/'bin'/'supervisorctl')


def force_symlink(target, link):
    if link.exists() or link.islink():
        link.unlink()
    target.symlink(link)


def ensure_folder(folder):
    if not folder.isdir():
        folder.makedirs()


class Deployment(object):

    DEPLOY_FOLDER_FMT = '%s.deploy'

    active_version_folder = None

    @property
    def folder(self):
        return self.sarge.home_path/(self.DEPLOY_FOLDER_FMT % self.name)

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
        self.active_version_folder = version_folder
        self.active_run_folder = run_folder = path(version_folder + '.run')
        run_folder.mkdir()
        symlink_path = self.sarge.run_links_folder/self.name
        if symlink_path.exists():
            symlink_path.readlink().rmtree()
        force_symlink(run_folder, symlink_path)
        self.sarge.on_activate_version.send(self, folder=version_folder)
        if 'tmp-wsgi-app' in self.config:
            app_import_name = self.config['tmp-wsgi-app']
            with open(version_folder/'quickapp.py', 'wb') as f:
                module_name, attribute_name = app_import_name.split(':')
                f.write(QUICK_WSGI_APP_TEMPLATE % {
                    'module_name': module_name,
                    'attribute_name': attribute_name,
                    'socket_path': str(run_folder/'wsgi-app.sock'),
                })
            self.config['command'] = "%s %s" % (sys.executable,
                                                version_folder/'quickapp.py')
        self.generate_supervisor_program_configuration()
        self.sarge.supervisorctl(['reread'])
        self.sarge.supervisorctl(['restart', self.name])

    def generate_supervisor_program_configuration(self):
        version_folder = self.active_version_folder
        run_folder = path(version_folder + '.run')
        with open(self.active_run_folder/SUPERVISOR_DEPLOY_CFG, 'wb') as f:
            extra_program_stuff = ""
            if self.config.get('autorestart', None) == 'always':
                extra_program_stuff = "autorestart = true\n"
            command = self.config.get('command')
            if command is not None:
                extra_program_stuff = "command = %s\n" % command
            f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                'name': self.name,
                'directory': version_folder,
                'run': run_folder,
                'extra_program_stuff': extra_program_stuff,
            })

    def start(self):
        self.sarge.supervisorctl(['start', self.name])

    def stop(self):
        self.sarge.supervisorctl(['stop', self.name])


def _get_named_object(name):
    module_name, attr_name = name.split(':')
    module = import_module(module_name)
    return getattr(module, attr_name)


class Sarge(object):

    def __init__(self, home_path):
        self.on_activate_version = blinker.Signal()
        self.on_initialize = blinker.Signal()
        self.home_path = home_path
        self.deployments = []
        self._configure()

    @property
    def run_links_folder(self):
        folder = self.home_path/RUN_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def _configure(self):
        if (self.home_path/DEPLOYMENT_CFG).isfile():
            with open(self.home_path/DEPLOYMENT_CFG, 'rb') as f:
                config = json.load(f)
        else:
            config = {}

        def iter_deployments():
            deployment_config_folder = self.home_path/DEPLOYMENT_CFG_DIR
            if deployment_config_folder.isdir():
                for depl_cfg_path in (deployment_config_folder).listdir():
                    yield json.loads(depl_cfg_path.bytes())

        for plugin_name in config.get('plugins', []):
            plugin_factory = _get_named_object(plugin_name)
            plugin_factory(self)
        for deployment_config in iter_deployments():
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

    def get_deployment(self, name):
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError

    def supervisorctl(self, cmd_args):
        base_args = [supervisorctl_path, '-c', self.home_path/SUPERVISORD_CFG]
        return subprocess.check_call(base_args + cmd_args)

    def status(self):
        self.supervisorctl(['status'])


class NginxPlugin(object):

    def __init__(self, sarge):
        self.sarge = sarge
        sarge.on_activate_version.connect(self.configure, weak=False)
        sarge.on_initialize.connect(self.initialize, weak=False)

    fcgi_params_path = '/etc/nginx/fastcgi_params'

    FOLDER_NAME = 'nginx.plugin'

    @property
    def folder(self):
        return self.sarge.home_path/self.FOLDER_NAME

    @property
    def sites_folder(self):
        return self.folder/'sites'

    def initialize(self, sarge):
        if not self.sites_folder.isdir():
            (self.sites_folder).makedirs()
        all_sites_conf = self.folder/'all_sites.conf'
        if not all_sites_conf.isfile():
            all_sites_conf.write_text('include %s/*;' % self.sites_folder)

    def configure(self, depl, folder):
        version_folder = folder
        run_folder = path(folder + '.run')

        app_config_path = version_folder/'sargeapp.yaml'
        if app_config_path.exists():
            with open(app_config_path, 'rb') as f:
                app_config = json.load(f)
        else:
            app_config = {}

        with open(run_folder/'nginx-site.conf', 'wb') as f:
            f.write('server {\n')

            nginx_options = app_config.get('nginx_options', {})
            for key, value in sorted(nginx_options.items()):
                f.write('  %s %s;\n' % (key, value))

            for entry in app_config.get('urlmap', []):
                if entry['type'] == 'static':
                    f.write('location %(url)s {\n'
                            '    alias %(version_folder)s/%(path)s;\n'
                            '}\n' % dict(entry, version_folder=version_folder))
                elif entry['type'] == 'wsgi':
                    socket_path = run_folder/'wsgi-app.sock'
                    f.write('location %(url)s {\n'
                            '    include %(fcgi_params_path)s;\n'
                            '    fastcgi_param PATH_INFO $fastcgi_script_name;\n'
                            '    fastcgi_param SCRIPT_NAME "";\n'
                            '    fastcgi_pass unix:%(socket_path)s;\n'
                            '}\n' % dict(entry,
                                         socket_path=socket_path,
                                         fcgi_params_path=self.fcgi_params_path))
                    depl.config['tmp-wsgi-app'] = entry['wsgi_app']

                elif entry['type'] == 'php':
                    socket_path = run_folder/'php.sock'
                    f.write('location %(url)s {\n'
                            '    include %(fcgi_params_path)s;\n'
                            '    fastcgi_param SCRIPT_FILENAME '
                                    '%(version_folder)s$fastcgi_script_name;\n'
                            '    fastcgi_param PATH_INFO $fastcgi_script_name;\n'
                            '    fastcgi_param SCRIPT_NAME "";\n'
                            '    fastcgi_pass unix:%(socket_path)s;\n'
                            '}\n' % dict(entry,
                                         socket_path=socket_path,
                                         version_folder=version_folder,
                                         fcgi_params_path=self.fcgi_params_path))

                    depl.config['command'] = (
                        '/usr/bin/spawn-fcgi -s %(socket_path)s '
                        '-f /usr/bin/php5-cgi -n'
                        % {'socket_path': socket_path})

                else:
                    raise NotImplementedError

            f.write('}\n')

        self.reload_nginx()

    def reload_nginx(self):
        subprocess.check_call(['service', 'nginx', 'reload'])


def init_cmd(sarge, args):
    sarge.on_initialize.send(sarge)
    (sarge.home_path/DEPLOYMENT_CFG_DIR).mkdir()
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
