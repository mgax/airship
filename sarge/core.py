import os
import sys
import logging
import json
import random
import string
import tempfile
from datetime import datetime
from importlib import import_module
from path import path
import blinker
import yaml
from .daemons import Supervisor
from . import signals


log = logging.getLogger(__name__)


DEPLOYMENT_CFG_DIR = 'deployments'
CFG_LINKS_FOLDER = 'active'
YAML_EXT = '.yaml'

QUICK_WSGI_APP_TEMPLATE = """\
#!%(python_bin)s
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
        self.folder = self.sarge._instance_folder(id_)
        var = self.sarge.home_path / 'var'
        self.run_folder = var / 'run' / id_
        self.appcfg_path = self.run_folder / 'appcfg.json'
        self.log_path = var / 'log' / (self.id_ + '.log')

    @property
    def meta(self):
        return self.config['meta']

    def get_appcfg(self):
        with self.appcfg_path.open('rb') as f:
            return json.load(f)

    def configure(self):
        self.run_folder.makedirs_p()
        appcfg = {}
        signals.instance_configuring.send(
            self.sarge, instance=self, appcfg=appcfg)
        with self.appcfg_path.open('wb') as f:
            json.dump(appcfg, f, indent=2)

    def start(self):
        log.info("Activating instance %r", self.id_)
        self.configure()
        appcfg = self.get_appcfg()
        signals.instance_will_start.send(self.sarge, instance=self,
                                                     appcfg=appcfg)
        if 'tmp-wsgi-app' in self.config:
            app_import_name = self.config['tmp-wsgi-app']
            script_path = self.folder / 'server'
            log.debug("Writing WSGI script for instance %r at %r.",
                      self.id_, script_path)
            with open(script_path, 'wb') as f:
                module_name, attribute_name = app_import_name.split(':')
                f.write(QUICK_WSGI_APP_TEMPLATE % {
                    'python_bin': sys.executable,
                    'module_name': module_name,
                    'attribute_name': attribute_name,
                    'socket_path': str(self.run_folder / 'wsgi-app.sock'),
                    'appcfg': appcfg,
                })
            script_path.chmod(0755)

        self.sarge.daemons.start_instance(self)

    def stop(self):
        self.sarge.daemons.stop_instance(self)
        signals.instance_has_stopped.send(self.sarge, instance=self)

    def destroy(self):
        self.sarge.daemons.remove_instance(self.id_)
        signals.instance_has_stopped.send(self.sarge, instance=self)
        signals.instance_will_be_destroyed.send(self.sarge, instance=self)
        if self.run_folder.isdir():
            self.run_folder.rmtree()
        if self.folder.isdir():
            self.folder.rmtree()
        self.sarge._instance_config_path(self.id_).unlink_p()

    def run(self, command):
        os.chdir(self.folder)
        environ = dict(os.environ, SARGEAPP_CFG=self.appcfg_path)
        prerun = self.config.get('prerun')
        shell_args = ['/bin/bash']
        if command:
            if prerun is not None:
                environ['BASH_ENV'] = self.config['prerun']
            shell_args += ['-c', command]
        else:
            if prerun is not None:
                shell_args += ['--rcfile', self.config['prerun']]
            else:
                shell_args += ['--norc']
        os.execve(shell_args[0], shell_args, environ)


class Sarge(object):
    """ The sarge object implements most operations performed by sarge. It acts
    as container for deployments.
    """

    def __init__(self, config):
        self.home_path = config['home']
        self.config = config
        self.daemons = Supervisor(self.home_path / 'etc')
        self._plugins = []
        for plugin_name in self.config.get('plugins', []):
            plugin_factory = _get_named_object(plugin_name)
            self._plugins.append(plugin_factory(self))

    @property
    def cfg_links_folder(self):
        folder = self.home_path / CFG_LINKS_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def _instance_config_path(self, instance_id):
        return self.home_path / DEPLOYMENT_CFG_DIR / (instance_id + YAML_EXT)

    def generate_supervisord_configuration(self):
        self.daemons.configure(self.home_path)

    def get_instance(self, instance_id):
        config_path = self._instance_config_path(instance_id)
        if not config_path.isfile():
            raise KeyError

        return Instance(instance_id, self, yaml.load(config_path.bytes()))

    def _instance_folder(self, id_):
        return self.home_path / id_

    def _generate_instance_id(self, id_prefix):
        def random_id(size=6, vocabulary=string.letters + string.digits):
            return ''.join(random.choice(vocabulary) for c in range(size))
        for c in range(10):
            id_ = id_prefix + random_id()
            try:
                self._instance_folder(id_).mkdir()
            except OSError:
                continue
            else:
                return id_
        else:
            raise RuntimeError("Failed to generate unique instance ID")

    def new_instance(self, config={}):
        (self.home_path / DEPLOYMENT_CFG_DIR).mkdir_p()
        meta = {'CREATION_TIME': datetime.utcnow().isoformat()}
        app_name = config.get('application_name')
        if app_name:
            meta['APPLICATION_NAME'] = app_name
            id_prefix = app_name + '-'
        else:
            id_prefix = ''
        instance_id = self._generate_instance_id(id_prefix)
        with open(self._instance_config_path(instance_id), 'wb') as f:
            json.dump({
                'require-services': config.get('services', {}),
                'urlmap': config.get('urlmap', []),
                'prerun': config.get('prerun', None),
                'meta': meta,
            }, f)
        instance = self.get_instance(instance_id)
        return instance

    def _iter_instance_ids(self):
        deployment_cfg_dir = self.home_path / DEPLOYMENT_CFG_DIR
        if not deployment_cfg_dir.exists():
            return
        for cfg_name in [p.name for p in deployment_cfg_dir.listdir()]:
            assert cfg_name.endswith(YAML_EXT)
            yield cfg_name[:-len(YAML_EXT)]

    def list_instances(self):
        instances = []
        for instance_id in self._iter_instance_ids():
            instance = self.get_instance(instance_id)
            instances.append({
                'id': instance.id_,
                'meta': instance.meta,
            })
        return {'instances': instances}


class VarFolderPlugin(object):

    def __init__(self, sarge):
        self.sarge = sarge
        signals.instance_configuring.connect(self.configure, sarge)

    def configure(self, sarge, instance, appcfg, **extra):
        var = instance.sarge.home_path / 'var'
        var_tmp = var / 'tmp'
        services = instance.config.get('require-services', {})

        for name, record in services.iteritems():
            if record['type'] == 'var-folder':
                var_tmp.makedirs_p()
                service_path = tempfile.mkdtemp(dir=var_tmp)
                if not service_path.isdir():
                    service_path.makedirs()
                appcfg[name.upper() + '_PATH'] = service_path

            elif record['type'] == 'persistent-folder':
                service_path = var / 'data' / name
                if not service_path.isdir():
                    service_path.makedirs()
                appcfg[name.upper() + '_PATH'] = service_path


class ListenPlugin(object):

    def __init__(self, sarge):
        self.sarge = sarge
        signals.instance_configuring.connect(self.configure, sarge)

    def configure(self, sarge, instance, appcfg, **extra):
        services = instance.config.get('require-services', {})
        for name, record in services.iteritems():
            if record['type'] == 'listen':
                if 'host' in record:
                    appcfg[name.upper() + '_HOST'] = record['host']
                if 'port' in record:
                    appcfg[name.upper() + '_PORT'] = record['port']


SARGE_SCRIPT = """#!/bin/bash
'{prefix}/bin/sarge' '{home}' "$@"
"""

SUPERVISORD_SCRIPT = """#!/bin/bash
'{prefix}/bin/supervisord' -c '{home}/etc/supervisor.conf'
"""

SUPERVISORCTL_SCRIPT = """#!/bin/bash
'{prefix}/bin/supervisorctl' -c '{home}/etc/supervisor.conf' $@
"""


def init_cmd(sarge, args):
    log.info("Initializing sarge folder at %r.", sarge.home_path)
    (sarge.home_path / 'etc').mkdir_p()
    sarge_yaml_path = sarge.home_path / 'etc' / 'sarge.yaml'
    if not sarge_yaml_path.isfile():
        with sarge_yaml_path.open('wb') as f:
            f.write('{\n  "plugins": [\n  ]\n}\n')
    (sarge.home_path / 'var').mkdir_p()
    (sarge.home_path / 'var' / 'log').mkdir_p()
    (sarge.home_path / 'var' / 'run').mkdir_p()
    (sarge.home_path / DEPLOYMENT_CFG_DIR).mkdir_p()
    signals.sarge_initializing.send(sarge)
    sarge.generate_supervisord_configuration()

    sarge_bin = sarge.home_path / 'bin'
    sarge_bin.makedirs()

    kw = {'home': sarge.home_path, 'prefix': sys.prefix}

    with open(sarge_bin / 'sarge', 'wb') as f:
        f.write(SARGE_SCRIPT.format(**kw))
        path(f.name).chmod(0755)

    with open(sarge_bin / 'supervisord', 'wb') as f:
        f.write(SUPERVISORD_SCRIPT.format(**kw))
        path(f.name).chmod(0755)

    with open(sarge_bin / 'supervisorctl', 'wb') as f:
        f.write(SUPERVISORCTL_SCRIPT.format(**kw))
        path(f.name).chmod(0755)


def new_cmd(sarge, args):
    print sarge.new_instance(json.loads(args.config)).id_


def list_cmd(sarge, args):
    print json.dumps(sarge.list_instances(), indent=2)


def configure_cmd(sarge, args):
    sarge.get_instance(args.id).configure()


def start_cmd(sarge, args):
    sarge.get_instance(args.id).start()


def stop_cmd(sarge, args):
    sarge.get_instance(args.id).stop()


def destroy_cmd(sarge, args):
    sarge.get_instance(args.id).destroy()


def run_cmd(sarge, args):
    sarge.get_instance(args.id).run(args.command)


def build_args_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sarge_home')
    subparsers = parser.add_subparsers()
    init_parser = subparsers.add_parser('init')
    init_parser.set_defaults(func=init_cmd)
    new_parser = subparsers.add_parser('new')
    new_parser.set_defaults(func=new_cmd)
    new_parser.add_argument('config')
    list_parser = subparsers.add_parser('list')
    list_parser.set_defaults(func=list_cmd)
    configure_parser = subparsers.add_parser('configure')
    configure_parser.set_defaults(func=configure_cmd)
    configure_parser.add_argument('id')
    start_parser = subparsers.add_parser('start')
    start_parser.set_defaults(func=start_cmd)
    start_parser.add_argument('id')
    stop_parser = subparsers.add_parser('stop')
    stop_parser.set_defaults(func=stop_cmd)
    stop_parser.add_argument('id')
    destroy_parser = subparsers.add_parser('destroy')
    destroy_parser.set_defaults(func=destroy_cmd)
    destroy_parser.add_argument('id')
    run_parser = subparsers.add_parser('run')
    run_parser.set_defaults(func=run_cmd)
    run_parser.add_argument('id')
    run_parser.add_argument('command', nargs='?')
    return parser


def set_up_logging(sarge_home):
    log_folder = sarge_home / 'var' / 'log'
    log_folder.makedirs_p()
    handler = logging.FileHandler(log_folder / 'sarge.log')
    log_format = "%(asctime)s %(levelname)s:%(name)s %(message)s"
    handler.setFormatter(logging.Formatter(log_format))
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)


def main(raw_arguments=None):
    parser = build_args_parser()
    args = parser.parse_args(raw_arguments or sys.argv[1:])
    sarge_home = path(args.sarge_home).abspath()
    set_up_logging(sarge_home)
    sarge_yaml_path = sarge_home / 'etc' / 'sarge.yaml'
    if sarge_yaml_path.isfile():
        with sarge_yaml_path.open('rb') as f:
            config = yaml.load(f)
    else:
        config = {}
    config['home'] = sarge_home
    sarge = Sarge(config)
    args.func(sarge, args)


if __name__ == '__main__':
    main()
