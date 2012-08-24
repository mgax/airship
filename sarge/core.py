import sys
import logging
import json
import random
import string
from importlib import import_module
from path import path
import blinker
import yaml
from .util import force_symlink
from .daemons import Supervisor


log = logging.getLogger(__name__)


SARGE_CFG = 'sargecfg.yaml'
DEPLOYMENT_CFG_DIR = 'deployments'
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


def _get_named_object(name):
    module_name, attr_name = name.split(':')
    module = import_module(module_name)
    return getattr(module, attr_name)


class Instance(object):

    def __init__(self, id_, sarge, config):
        self.id_ = id_
        self.sarge = sarge
        self.config = config
        self.folder = self.sarge._instance_folder(id_) / '1'
        self.run_folder = self.sarge.home_path / 'var' / 'run' / id_

    def start(self):
        version_folder = self.folder
        log.info("Activating instance %r", self.id_)
        self.run_folder.makedirs_p()
        cfg_folder = path(version_folder + '.cfg')
        cfg_folder.mkdir()
        symlink_path = self.sarge.cfg_links_folder / self.id_
        force_symlink(cfg_folder, symlink_path)
        share = {'programs': self.config.get('programs', [])}
        services = dict((s['name'], s)
                        for s in self.config.get('services', []))
        self._appcfg = {'services': services}
        self.sarge.on_instance_start.send(self, share=share, appcfg=self._appcfg)
        if 'tmp-wsgi-app' in self.config:
            app_import_name = self.config['tmp-wsgi-app']
            script_path = version_folder / 'quickapp.py'
            log.debug("Writing WSGI script for instance %r at %r.",
                      self.id_, script_path)
            with open(script_path, 'wb') as f:
                module_name, attribute_name = app_import_name.split(':')
                f.write(QUICK_WSGI_APP_TEMPLATE % {
                    'module_name': module_name,
                    'attribute_name': attribute_name,
                    'socket_path': str(self.run_folder / 'wsgi-app.sock'),
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
        self.sarge.daemons.restart_deployment(self.id_)

    def write_supervisor_program_config(self, version_folder, share):
        cfg_folder = path(version_folder + '.cfg')

        programs = []
        for program_cfg in share['programs']:
            program_name = self.id_ + '_' + program_cfg['name']
            program_config = {
                'name': program_name,
                'directory': version_folder,
                'run': self.run_folder,
                'environment': 'SARGEAPP_CFG="%s"\n' % (cfg_folder / APP_CFG),
                'command': program_cfg['command'],
            }
            programs.append((program_name, program_config))

        self.sarge.daemons.configure_deployment(self.id_, programs)


class Sarge(object):
    """ The sarge object implements most operations performed by sarge. It acts
    as container for deployments.
    """

    def __init__(self, config):
        self.on_instance_start = blinker.Signal()
        self.on_initialize = blinker.Signal()
        self.home_path = config['home']
        self.config = config
        self.daemons = Supervisor(self.home_path / 'etc')
        for plugin_name in self.config.get('plugins', []):
            plugin_factory = _get_named_object(plugin_name)
            plugin_factory(self)

    @property
    def cfg_links_folder(self):
        folder = self.home_path / CFG_LINKS_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def generate_supervisord_configuration(self):
        self.daemons.configure(self.home_path)

    def get_instance(self, instance_id):
        config_path = (self.home_path /
                       DEPLOYMENT_CFG_DIR /
                       (instance_id + '.yaml'))
        if not config_path.isfile():
            raise KeyError

        return Instance(instance_id, self, yaml.load(config_path.bytes()))

    def _instance_folder(self, id_):
        return self.home_path / (id_ + '.deploy')

    def _generate_instance_id(self):
        def random_id(size=6, vocabulary=string.letters + string.digits):
            return ''.join(random.choice(vocabulary) for c in range(size))
        for c in range(10):
            id_ = random_id()
            try:
                self._instance_folder(id_).mkdir()
            except OSError:
                continue
            else:
                return id_
        else:
            raise RuntimeError("Failed to generate unique instance ID")

    def new_instance(self, config={}):
        instance_id = self._generate_instance_id()
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
        instance = self.get_instance(instance_id)
        instance.folder.mkdir()
        return instance


class VarFolderPlugin(object):

    def __init__(self, sarge):
        self.sarge = sarge
        sarge.on_instance_start.connect(self.activate_deployment, weak=False)

    def activate_deployment(self, instance, appcfg, **extra):
        var = instance.sarge.home_path / 'var'
        var_instance = var / instance.id_
        services = instance.config.get('require-services', {})

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
    log.info("Initializing sarge folder at %r.", sarge.home_path)
    (sarge.home_path / 'etc').mkdir_p()
    (sarge.home_path / DEPLOYMENT_CFG_DIR).mkdir_p()
    sarge.on_initialize.send(sarge)
    sarge.generate_supervisord_configuration()


def new_instance_cmd(sarge, args):
    print sarge.new_instance(json.loads(args.config)).folder


def start_instance_cmd(sarge, args):
    sarge.get_instance(args.id).start()


def build_args_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sarge_home')
    subparsers = parser.add_subparsers()
    init_parser = subparsers.add_parser('init')
    init_parser.set_defaults(func=init_cmd)
    new_instance_parser = subparsers.add_parser('new_instance')
    new_instance_parser.set_defaults(func=new_instance_cmd)
    new_instance_parser.add_argument('config')
    start_instance_parser = subparsers.add_parser('start_instance')
    start_instance_parser.set_defaults(func=start_instance_cmd)
    start_instance_parser.add_argument('id')
    return parser


def set_up_logging(sarge_home_path):
    handler = logging.FileHandler(sarge_home_path / 'sarge.log')
    log_format = "%(asctime)s %(levelname)s:%(name)s %(message)s"
    handler.setFormatter(logging.Formatter(log_format))
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)


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
