import os
import sys
import logging
import json
import random
import string
from datetime import datetime
from importlib import import_module
from path import path
import yaml
from .daemons import Supervisor


log = logging.getLogger(__name__)


DEPLOYMENT_CFG_DIR = 'deployments'
CFG_LINKS_FOLDER = 'active'
YAML_EXT = '.yaml'
RUN_RC_NAME = '.runrc'


def _get_named_object(name):
    module_name, attr_name = name.split(':')
    module = import_module(module_name)
    return getattr(module, attr_name)


def random_id(size=6, vocabulary=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(vocabulary) for c in range(size))


class Instance(object):

    def __init__(self, id_, sarge, config):
        self.id_ = id_
        self.sarge = sarge
        self.config = config
        self.folder = self.sarge._instance_folder(id_)
        var = self.sarge.home_path / 'var'
        self.run_folder = var / 'run' / id_
        self.log_path = var / 'log' / (self.id_ + '.log')

    @property
    def meta(self):
        return self.config['meta']

    @property
    def port(self):
        return self.config['port']

    def _new(self):
        self.sarge.daemons.configure_instance_stopped(self)

    def configure(self):
        self.run_folder.makedirs_p()

    def start(self):
        log.info("Activating instance %r", self.id_)
        self.configure()
        self.sarge.daemons.configure_instance_running(self)

    def stop(self):
        self.sarge.daemons.configure_instance_stopped(self)

    def trigger(self):
        self.sarge.daemons.trigger_instance(self)

    def destroy(self):
        self.sarge.daemons.remove_instance(self.id_)
        if self.run_folder.isdir():
            self.run_folder.rmtree()
        if self.folder.isdir():
            self.folder.rmtree()
        self.sarge._instance_config_path(self.id_).unlink_p()

    def _get_config(self):
        config_json = self.sarge.home_path / 'etc' / 'app' / 'config.json'
        if not config_json.isfile():
            return {}

        with config_json.open('rb') as f:
            return json.load(f)

    def run(self, command):
        os.chdir(self.folder)
        environ = dict(os.environ)
        environ.update(self._get_config())
        environ['PORT'] = str(self.port)
        shell_args = ['/bin/bash']
        if command:
            environ['BASH_ENV'] = RUN_RC_NAME
            shell_args += ['-c', command]
        else:
            shell_args += ['--rcfile', RUN_RC_NAME]
        os.execve(shell_args[0], shell_args, environ)


class Sarge(object):
    """ The sarge object implements most operations performed by sarge. It acts
    as container for deployments.
    """

    def __init__(self, config):
        self.home_path = config['home']
        self.config = config
        self.daemons = Supervisor(self.home_path / 'etc')

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

    def _get_instance_by_id(self, instance_id):
        config_path = self._instance_config_path(instance_id)
        if not config_path.isfile():
            raise KeyError

        return Instance(instance_id, self, yaml.load(config_path.bytes()))

    def get_instance(self, name):
        try:
            return self._get_instance_by_id(name)

        except KeyError:
            for instance_id in self._iter_instance_ids():
                instance = self._get_instance_by_id(instance_id)
                if name == instance.meta.get('APPLICATION_NAME'):
                    return instance

            else:
                raise KeyError

    def _instance_folder(self, id_):
        return self.home_path / id_

    def _generate_instance_id(self, id_prefix):
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

    PORT_RANGE = (5000, 5099)

    def _open_ports_db(self):
        import kv
        return kv.KV(self.home_path / 'etc' / 'ports.db')

    def _allocate_port(self, instance_id):
        ports_db = self._open_ports_db()
        with ports_db.lock():
            for port in xrange(*self.PORT_RANGE):
                if port in ports_db:
                    continue
                ports_db[port] = instance_id
                return port

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
                'meta': meta,
                'port': self._allocate_port(instance_id),
            }, f)
        instance = self._get_instance_by_id(instance_id)
        instance._new()
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
            instance = self._get_instance_by_id(instance_id)
            instances.append({
                'id': instance.id_,
                'meta': instance.meta,
            })
        return {'instances': instances}


SARGE_SCRIPT = """#!/bin/bash
exec '{prefix}/bin/sarge' '{home}' "$@"
"""

SUPERVISORD_SCRIPT = """#!/bin/bash
exec '{prefix}/bin/supervisord' -c '{home}/etc/supervisor.conf'
"""

SUPERVISORCTL_SCRIPT = """#!/bin/bash
exec '{prefix}/bin/supervisorctl' -c '{home}/etc/supervisor.conf' $@
"""


def init_cmd(sarge, args):
    log.info("Initializing sarge folder at %r.", sarge.home_path)
    (sarge.home_path / 'etc').mkdir_p()
    sarge_yaml_path = sarge.home_path / 'etc' / 'sarge.yaml'
    if not sarge_yaml_path.isfile():
        with sarge_yaml_path.open('wb') as f:
            f.write('{}\n')
    (sarge.home_path / 'var').mkdir_p()
    (sarge.home_path / 'var' / 'log').mkdir_p()
    (sarge.home_path / 'var' / 'run').mkdir_p()
    (sarge.home_path / DEPLOYMENT_CFG_DIR).mkdir_p()
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


def trigger_cmd(sarge, args):
    sarge.get_instance(args.id).trigger()


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
    trigger_parser = subparsers.add_parser('trigger')
    trigger_parser.set_defaults(func=trigger_cmd)
    trigger_parser.add_argument('id')
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
