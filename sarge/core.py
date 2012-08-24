import sys
import logging
import json
from importlib import import_module
from path import path
import blinker
import yaml
from .util import force_symlink
from .daemons import SUPERVISOR_DEPLOY_CFG, Supervisor


sarge_log = logging.getLogger('sarge')


SARGE_CFG = 'sargecfg.yaml'
DEPLOYMENT_CFG_DIR = 'deployments'
SUPERVISORD_CFG = 'supervisord.conf'
CFG_LINKS_FOLDER = 'active'
APP_CFG = 'appcfg.json'

QUICK_WSGI_APP_TEMPLATE = """\
from flup.server.fcgi import WSGIServer
from importlib import import_module
appcfg = %(appcfg)r
app_factory = getattr(import_module(%(module_name)r), %(attribute_name)r)
app = app_factory(appcfg)
server = WSGIServer(app, bindAddress=%(socket_path)r, umask=0)
server.run()
"""


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
                return version_folder

    def activate_version(self, version_folder):
        """ Activate a version folder. Creates a runtime folder, generates
        various configuration files, then notifies supervisor to restart any
        processes for this deployment. """
        self.log.info("Activating version at %r for deployment %r",
                      version_folder, self.name)
        run_folder = path(version_folder + '.run')
        run_folder.mkdir()
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
        self.sarge.daemons.update()
        self.sarge.daemons.restart_deployment(self.name)

    def write_supervisor_program_config(self, version_folder, share):
        run_folder = path(version_folder + '.run')
        cfg_folder = path(version_folder + '.cfg')
        supervisor_deploy_cfg_path = cfg_folder / SUPERVISOR_DEPLOY_CFG
        self.log.debug("Writing supervisor configuration fragment for "
                       "deployment %r at %r.",
                       self.name, supervisor_deploy_cfg_path)

        programs = []
        for program_cfg in share['programs']:
            program_name = self.name + '_' + program_cfg['name']
            program_config = {
                'name': program_name,
                'directory': version_folder,
                'run': run_folder,
                'environment': 'SARGEAPP_CFG="%s"\n' % (cfg_folder / APP_CFG),
                'command': program_cfg['command'],
            }
            programs.append((program_name, program_config))

        self.sarge.daemons.configure_deployment(self.name, cfg_folder, programs)

    def start(self):
        self.log.info("Starting deployment %r.", self.name)
        self.sarge.daemons.start_deployment(self.name)


def _get_named_object(name):
    module_name, attr_name = name.split(':')
    module = import_module(module_name)
    return getattr(module, attr_name)


class Instance(object):

    def __init__(self, deployment):
        self.deployment = deployment

    @property
    def folder(self):
        return self.deployment.folder / '1'

    @property
    def id_(self):
        return self.deployment.name

    def start(self):
        self.deployment.activate_version(self.folder)


class Sarge(object):
    """ The sarge object implements most operations performed by sarge. It acts
    as container for deployments.
    """

    log = logging.getLogger('sarge.Sarge')
    log.setLevel(logging.DEBUG)

    def __init__(self, config):
        self.on_activate_version = blinker.Signal()
        self.on_initialize = blinker.Signal()
        self.home_path = config['home']
        self.deployments = []
        self.config = config
        self._load_deployments()
        self.daemons = Supervisor(self.home_path / SUPERVISORD_CFG)

    @property
    def cfg_links_folder(self):
        folder = self.home_path / CFG_LINKS_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def _load_deployments(self):
        def iter_deployments():
            deployment_config_folder = self.home_path / DEPLOYMENT_CFG_DIR
            if deployment_config_folder.isdir():
                for depl_cfg_path in (deployment_config_folder).listdir():
                    if depl_cfg_path.ext == '.yaml':
                        yield yaml.load(depl_cfg_path.bytes())

        for plugin_name in self.config.get('plugins', []):
            plugin_factory = _get_named_object(plugin_name)
            plugin_factory(self)
        self.deployments[:] = []
        for deployment_config in iter_deployments():
            depl = Deployment()
            depl.name = deployment_config['name']
            depl.config = deployment_config
            depl.sarge = self
            self.deployments.append(depl)

    def generate_supervisord_configuration(self):
        self.log.debug("Writing main supervisord configuration file at %r.",
                       self.home_path / SUPERVISORD_CFG)
        self.daemons.configure(**{
            'home_path': self.home_path,
            'include_files': (path(CFG_LINKS_FOLDER) /
                              '*' /
                              SUPERVISOR_DEPLOY_CFG),
        })

    def get_deployment(self, name):
        """ Retrieve a :class:`~sarge.Deployment` by name. """
        for depl in self.deployments:
            if depl.name == name:
                return depl
        else:
            raise KeyError

    def get_instance(self, instance_id):
        deployment = self.get_deployment(instance_id)
        return Instance(deployment)

    def new_instance(self, config={}):
        instance_id = 'inst'  # TODO make it random and unique
        deploy_cfg_dir = self.home_path / DEPLOYMENT_CFG_DIR
        deploy_cfg_dir.mkdir_p()
        instance_cfg_path = (self.home_path /
                             DEPLOYMENT_CFG_DIR /
                             instance_id+'.yaml')
        with open(instance_cfg_path, 'wb') as f:
            services = config.get('services')
            json.dump({
                'name': instance_id,
                'programs': [
                    {'name': 'daemon', 'command': 'run'},
                ],
                'require-services': services,
            }, f)
        self._load_deployments()
        instance = self.get_instance(instance_id)
        version_folder = instance.deployment.new_version()
        assert instance.folder == version_folder
        return instance


class VarFolderPlugin(object):

    log = logging.getLogger('sarge.VarFolderPlugin')
    log.setLevel(logging.DEBUG)

    def __init__(self, sarge):
        self.sarge = sarge
        sarge.on_activate_version.connect(self.activate_deployment, weak=False)

    def activate_deployment(self, depl, appcfg, **extra):
        var = depl.sarge.home_path / 'var'
        var_instance = var / depl.name
        services = depl.config.get('require-services', {})

        for name, record in services.iteritems():
            if record['type'] == 'var-folder':
                service_path = var_instance / name
                if not service_path.isdir():
                    service_path.makedirs()
                appcfg['services'][name] = service_path

            elif record['type'] == 'persistent-folder':
                service_path = var / name
                if not service_path.isdir():
                    service_path.makedirs()
                appcfg['services'][name] = service_path


def init_cmd(sarge, args):
    sarge.log.info("Initializing sarge folder at %r.", sarge.home_path)
    sarge.on_initialize.send(sarge)
    (sarge.home_path / DEPLOYMENT_CFG_DIR).mkdir()
    sarge.generate_supervisord_configuration()


def new_version_cmd(sarge, args):
    print sarge.get_deployment(args.name).new_version()


def new_instance_cmd(sarge, args):
    print sarge.new_instance().folder


def start_instance_cmd(sarge, args):
    sarge.get_instance(args.id).start()


def start_cmd(sarge, args):
    sarge.get_deployment(args.name).start()


def build_args_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sarge_home')
    subparsers = parser.add_subparsers()
    init_parser = subparsers.add_parser('init')
    init_parser.set_defaults(func=init_cmd)
    new_instance_parser = subparsers.add_parser('new_instance')
    new_instance_parser.set_defaults(func=new_instance_cmd)
    start_instance_parser = subparsers.add_parser('start_instance')
    start_instance_parser.set_defaults(func=start_instance_cmd)
    start_instance_parser.add_argument('id')
    new_version_parser = subparsers.add_parser('new_version')
    new_version_parser.set_defaults(func=new_version_cmd)
    new_version_parser.add_argument('name')
    start_parser = subparsers.add_parser('start')
    start_parser.set_defaults(func=start_cmd)
    start_parser.add_argument('name')
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
    with open(sarge_home_path / SARGE_CFG, 'rb') as f:
        config = yaml.load(f)
    config['home'] = sarge_home_path
    sarge = Sarge(config)
    args.func(sarge, args)


if __name__ == '__main__':
    main()
