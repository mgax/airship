import sys
import subprocess
import logging
import json
from importlib import import_module
from path import path
import blinker
import yaml
from .util import force_symlink


sarge_log = logging.getLogger('sarge')


SARGE_CFG = 'sargecfg.yaml'
DEPLOYMENT_CFG_DIR = 'deployments'
SUPERVISORD_CFG = 'supervisord.conf'
SUPERVISOR_DEPLOY_CFG = 'supervisor_deploy.conf'
CFG_LINKS_FOLDER = 'active'
APP_CFG = 'appcfg.json'

SUPERVISORD_CFG_TEMPLATE = """\
[unix_http_server]
file = %(home_path)s/supervisord.sock
%(extra_server_stuff)s

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
files = """ + path(CFG_LINKS_FOLDER) / '*' / SUPERVISOR_DEPLOY_CFG + """
"""

SUPERVISORD_PROGRAM_TEMPLATE = """\
[program:%(name)s]
directory = %(directory)s
redirect_stderr = true
stdout_logfile = %(run)s/stdout.log
startsecs = 2
startretries = 0
autostart = false
%(extra_program_stuff)s
"""


QUICK_WSGI_APP_TEMPLATE = """\
from flup.server.fcgi import WSGIServer
from importlib import import_module
appcfg = %(appcfg)r
app_factory = getattr(import_module(%(module_name)r), %(attribute_name)r)
app = app_factory(appcfg)
server = WSGIServer(app, bindAddress=%(socket_path)r, umask=0)
server.run()
"""

supervisorctl_path = str(path(sys.prefix).abspath() / 'bin' / 'supervisorctl')


class Deployment(object):
    """ Web application that is deployed using sarge. It has a configuration
    file and a number of version folders. Only one version is "active" and
    running. """

    log = logging.getLogger('sarge.Deployment')
    log.setLevel(logging.DEBUG)

    DEPLOY_FOLDER_FMT = '%s.deploy'

    @property
    def folder(self):
        return self.sarge.home_path / (self.DEPLOY_FOLDER_FMT % self.name)

    def new_version(self):
        """ Create a new version folder. Copy application code there and then
        call :meth:`activate_version`. """
        # TODO make sure we don't reuse version IDs. we probably need to
        # save the counter to a file in `self.folder`.
        import itertools
        for c in itertools.count(1):
            version_folder = self.folder / str(c)
            if not version_folder.exists():
                self.log.info("New version folder for deployment %r at %r.",
                              self.name, version_folder)
                version_folder.makedirs()
                # TODO test
                subprocess.check_call(['chown', self.config['user'] + ':',
                                       version_folder])
                return version_folder

    def activate_version(self, version_folder):
        """ Activate a version folder. Creates a runtime folder, generates
        various configuration files, then notifies supervisor to restart any
        processes for this deployment. """
        self.log.info("Activating version at %r for deployment %r",
                      version_folder, self.name)
        run_folder = path(version_folder + '.run')
        run_folder.mkdir()
        subprocess.check_call(['chown', self.config['user'] + ':',
                               run_folder])
        cfg_folder = path(version_folder + '.cfg')
        cfg_folder.mkdir()
        symlink_path = self.sarge.cfg_links_folder / self.name
        force_symlink(cfg_folder, symlink_path)
        share = {'programs': self.config.get('programs', [])}
        services = dict((s['name'], s)
                        for s in self.config.get('services', []))
        self._appcfg = {'services': services}
        self.sarge.on_activate_version.send(self,
                                            folder=version_folder,
                                            share=share,
                                            appcfg=self._appcfg)
        if 'tmp-wsgi-app' in self.config:
            app_import_name = self.config['tmp-wsgi-app']
            script_path = version_folder / 'quickapp.py'
            self.log.debug("Writing WSGI script for deployment %r at %r.",
                           self.name, script_path)
            with open(script_path, 'wb') as f:
                module_name, attribute_name = app_import_name.split(':')
                f.write(QUICK_WSGI_APP_TEMPLATE % {
                    'module_name': module_name,
                    'attribute_name': attribute_name,
                    'socket_path': str(run_folder / 'wsgi-app.sock'),
                    'appcfg': self._appcfg,
                })

            share['programs'].append({
                'name': 'fcgi_wsgi',
                'command': "%s %s" % (sys.executable,
                                      version_folder / 'quickapp.py'),
            })

        with (cfg_folder / APP_CFG).open('wb') as f:
            json.dump(self._appcfg, f, indent=2)

        self.write_supervisor_program_config(version_folder, share)
        self.sarge.supervisorctl(['update'])
        self.sarge.supervisorctl(['restart', self.name + ':*'])

    def write_supervisor_program_config(self, version_folder, share):
        run_folder = path(version_folder + '.run')
        cfg_folder = path(version_folder + '.cfg')
        supervisor_deploy_cfg_path = cfg_folder / SUPERVISOR_DEPLOY_CFG
        self.log.debug("Writing supervisor configuration fragment for "
                       "deployment %r at %r.",
                       self.name, supervisor_deploy_cfg_path)
        with open(supervisor_deploy_cfg_path, 'wb') as f:
            program_name_list = []
            for program_cfg in share['programs']:
                extra_program_stuff = ""
                extra_program_stuff += \
                    'environment=SARGEAPP_CFG="%s"\n' % (cfg_folder / APP_CFG)
                extra_program_stuff += ("command = %s\n" %
                                        program_cfg['command'])
                if self.config.get('autorestart', None) == 'always':
                    # TODO this should be specified in 'program_cfg'
                    extra_program_stuff += "autorestart = true\n"
                extra_program_stuff += "user = %s\n" % self.config['user']
                program_name = self.name + '_' + program_cfg['name']
                f.write(SUPERVISORD_PROGRAM_TEMPLATE % {
                    'name': program_name,
                    'directory': version_folder,
                    'run': run_folder,
                    'extra_program_stuff': extra_program_stuff,
                })
                program_name_list.append(program_name)

            f.write("[group:%(name)s]\nprograms = %(programs)s\n" % {
                'name': self.name,
                'programs': ','.join(program_name_list),
            })

    def start(self):
        self.log.info("Starting deployment %r.", self.name)
        self.sarge.supervisorctl(['start', self.name + ':*'])

    def stop(self):
        self.log.info("Stopping deployment %r.", self.name)
        self.sarge.supervisorctl(['stop', self.name + ':*'])


def _get_named_object(name):
    module_name, attr_name = name.split(':')
    module = import_module(module_name)
    return getattr(module, attr_name)


class Sarge(object):
    """ The sarge object implements most operations performed by sarge. It acts
    as container for deployments.
    """

    log = logging.getLogger('sarge.Sarge')
    log.setLevel(logging.DEBUG)

    def __init__(self, home_path):
        self.on_activate_version = blinker.Signal()
        self.on_initialize = blinker.Signal()
        self.home_path = home_path
        self.deployments = []
        self._configure()

    @property
    def cfg_links_folder(self):
        folder = self.home_path / CFG_LINKS_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def _configure(self):
        with open(self.home_path / SARGE_CFG, 'rb') as f:
            config = yaml.load(f)

        def iter_deployments():
            deployment_config_folder = self.home_path / DEPLOYMENT_CFG_DIR
            if deployment_config_folder.isdir():
                for depl_cfg_path in (deployment_config_folder).listdir():
                    if depl_cfg_path.ext == '.yaml':
                        yield yaml.load(depl_cfg_path.bytes())

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
        supervisord_cfg_path = self.home_path / SUPERVISORD_CFG
        self.log.debug("Writing main supervisord configuration file at %r.",
                       supervisord_cfg_path)
        with open(supervisord_cfg_path, 'wb') as f:
            extra_server_stuff = ""

            f.write(SUPERVISORD_CFG_TEMPLATE % {
                'home_path': self.home_path,
                'extra_server_stuff': extra_server_stuff,
            })

    def get_deployment(self, name):
        """ Retrieve a :class:`~sarge.Deployment` by name. """
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError

    def supervisorctl(self, cmd_args):
        self.log.debug("Invoking supervisorctl with arguments %r.", cmd_args)
        base_args = [supervisorctl_path,
                     '-c', self.home_path / SUPERVISORD_CFG]
        return subprocess.check_call(base_args + cmd_args)

    def status(self):
        self.supervisorctl(['status'])


class VarFolderPlugin(object):

    log = logging.getLogger('sarge.VarFolderPlugin')
    log.setLevel(logging.DEBUG)

    def __init__(self, sarge):
        self.sarge = sarge
        sarge.on_activate_version.connect(self.activate_deployment, weak=False)

    def activate_deployment(self, depl, appcfg, **extra):
        var = depl.sarge.home_path / 'var' / depl.name
        for record in depl.config.get('require-services', []):
            if record['type'] == 'var-folder':
                name = record['name']
                service_path = var / name
                if not service_path.isdir():
                    service_path.makedirs()
                appcfg['services'][name] = service_path


def init_cmd(sarge, args):
    sarge.log.info("Initializing sarge folder at %r.", sarge.home_path)
    sarge.on_initialize.send(sarge)
    (sarge.home_path / DEPLOYMENT_CFG_DIR).mkdir()
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


def set_up_logging(sarge_home_path):
    handler = logging.FileHandler(sarge_home_path / 'sarge.log')
    log_format = "%(asctime)s %(levelname)s:%(name)s %(message)s"
    handler.setFormatter(logging.Formatter(log_format))
    handler.setLevel(logging.DEBUG)
    sarge_log.addHandler(handler)


def main(raw_arguments=None):
    parser = build_args_parser()
    args = parser.parse_args(raw_arguments or sys.argv[1:])
    sarge_home_path = path(args.sarge_home).abspath()
    set_up_logging(sarge_home_path)
    sarge = Sarge(sarge_home_path)
    args.func(sarge, args)


if __name__ == '__main__':
    main()