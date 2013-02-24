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
from kv import KV
import pkg_resources
from .daemons import Supervisor
from . import deployer


log = logging.getLogger(__name__)


CFG_LINKS_FOLDER = 'active'
YAML_EXT = '.yaml'


def _get_named_object(name):
    module_name, attr_name = name.split(':')
    module = import_module(module_name)
    return getattr(module, attr_name)


def random_id(size=6, vocabulary=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(vocabulary) for c in range(size))


class Bucket(object):

    def __init__(self, id_, airship, config):
        self.id_ = id_
        self.airship = airship
        self.config = config
        self.folder = self.airship._bucket_folder(id_)
        var = self.airship.home_path / 'var'
        self.run_folder = var / 'run' / id_
        self.log_path = var / 'log' / (self.id_ + '.log')
        self.process_types = {}
        self._read_procfile()

    def _read_procfile(self):
        procfile_path = self.folder / 'Procfile'
        if procfile_path.isfile():
            with procfile_path.open('rb') as f:
                for line in f:
                    (procname, cmd) = line.split(':', 1)
                    self.process_types[procname.strip()] = cmd.strip()

    @property
    def meta(self):
        return self.config['meta']

    def configure(self):
        self.run_folder.makedirs_p()

    def start(self):
        log.info("Activating bucket %r", self.id_)
        self.configure()
        self.airship.daemons.configure_bucket_running(self)

    def stop(self):
        self.airship.daemons.configure_bucket_stopped(self)

    def trigger(self):
        self.airship.daemons.trigger_bucket(self)

    def destroy(self):
        self.airship.daemons.remove_bucket(self.id_)
        if self.run_folder.isdir():
            self.run_folder.rmtree()
        if self.folder.isdir():
            self.folder.rmtree()
        self.airship.buckets_db.pop(self.id_, None)

    def run(self, command):
        os.chdir(self.folder)
        environ = dict(os.environ)
        environ.update(self.airship.config.get('env') or {})
        venv = self.folder / '_virtualenv'
        if venv.isdir():
            environ['PATH'] = ((venv / 'bin') + ':' + environ['PATH'])
        shell_args = ['/bin/bash']
        if command:
            if command in self.process_types:
                procname = command
                port_map = self.airship.config.get('port_map', {})
                if procname in port_map:
                    environ['PORT'] = str(port_map[procname])
                command = self.process_types[procname]
            shell_args += ['-c', command]
        os.execve(shell_args[0], shell_args, environ)


_newest = object()


class Airship(object):
    """ The airship object implements most operations performed by airship. It
    acts as container for deployments.
    """

    def __init__(self, config):
        self.home_path = config['home']
        self.var_path = self.home_path / 'var'
        self.log_path = self.var_path / 'log'
        self.config = config
        etc = self.home_path / 'etc'
        etc.mkdir_p()
        self.buckets_db = KV(etc / 'buckets.db', table='bucket')
        self.daemons = Supervisor(etc)

    @property
    def cfg_links_folder(self):
        folder = self.home_path / CFG_LINKS_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def initialize(self):
        self.generate_supervisord_configuration()

    def generate_supervisord_configuration(self):
        self.daemons.configure(self.home_path)

    def _get_bucket_by_id(self, bucket_id):
        config = self.buckets_db[bucket_id]
        return Bucket(bucket_id, self, config)

    def get_bucket(self, name=_newest):
        if name is _newest:
            name = max(self.buckets_db)
        return self._get_bucket_by_id(name)

    def _bucket_folder(self, id_):
        return self.home_path / id_

    def _generate_bucket_id(self):
        for c in range(10):
            id_ = random_id()
            try:
                self._bucket_folder(id_).mkdir()
            except OSError:
                continue
            else:
                return id_
        else:
            raise RuntimeError("Failed to generate unique bucket ID")

    def new_bucket(self, config={}):
        meta = {'CREATION_TIME': datetime.utcnow().isoformat()}
        bucket_id = self._generate_bucket_id()
        self.buckets_db[bucket_id] = {
            'meta': meta,
        }
        bucket = self._get_bucket_by_id(bucket_id)
        return bucket

    def list_buckets(self):
        return {'buckets': [{'id': id_} for id_ in self.buckets_db]}


def load_plugins():
    for entry_point in pkg_resources.iter_entry_points('airship_plugins'):
        callback = entry_point.load()
        callback()


AIRSHIP_SCRIPT = """#!/bin/bash
exec '{prefix}/bin/airship' '{home}' "$@"
"""

SUPERVISORD_SCRIPT = """#!/bin/bash
exec '{prefix}/bin/supervisord' -c '{home}/etc/supervisor.conf'
"""

SUPERVISORCTL_SCRIPT = """#!/bin/bash
exec '{prefix}/bin/supervisorctl' -c '{home}/etc/supervisor.conf' $@
"""


def init_cmd(airship, args):
    log.info("Initializing airship folder at %r.", airship.home_path)
    airship_yaml_path = airship.home_path / 'etc' / 'airship.yaml'
    if not airship_yaml_path.isfile():
        with airship_yaml_path.open('wb') as f:
            f.write('{}\n')
    airship.var_path.mkdir_p()
    airship.log_path.mkdir_p()
    (airship.var_path / 'run').mkdir_p()
    airship.initialize()

    airship_bin = airship.home_path / 'bin'
    airship_bin.makedirs()

    kw = {'home': airship.home_path, 'prefix': sys.prefix}

    with open(airship_bin / 'airship', 'wb') as f:
        f.write(AIRSHIP_SCRIPT.format(**kw))
        path(f.name).chmod(0755)

    with open(airship_bin / 'supervisord', 'wb') as f:
        f.write(SUPERVISORD_SCRIPT.format(**kw))
        path(f.name).chmod(0755)

    with open(airship_bin / 'supervisorctl', 'wb') as f:
        f.write(SUPERVISORCTL_SCRIPT.format(**kw))
        path(f.name).chmod(0755)


def new_cmd(airship, args):
    print airship.new_bucket(json.loads(args.config)).id_


def list_cmd(airship, args):
    print json.dumps(airship.list_buckets(), indent=2)


def configure_cmd(airship, args):
    airship.get_bucket(args.id).configure()


def start_cmd(airship, args):
    airship.get_bucket(args.id).start()


def stop_cmd(airship, args):
    airship.get_bucket(args.id).stop()


def trigger_cmd(airship, args):
    airship.get_bucket(args.id).trigger()


def destroy_cmd(airship, args):
    airship.get_bucket(args.id).destroy()


def run_cmd(airship, args):
    airship.get_bucket(args.id).run(args.command)


def deploy_cmd(airship, args):
    try:
        deployer.deploy(airship, args.tarfile)
    except deployer.DeployError, e:
        print "Deployment failed:", e.message
        try:
            e.bucket.destroy()
        except:
            print ("Error while cleaning up failed deployment %s."
                   % e.bucket.id_)
        else:
            print "Cleaned up failed deployment."


def build_args_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('airship_home')
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
    deploy_parser = subparsers.add_parser('deploy')
    deploy_parser.set_defaults(func=deploy_cmd)
    deploy_parser.add_argument('tarfile')
    return parser


def set_up_logging(airship_home):
    log_folder = airship_home / 'var' / 'log'
    log_folder.makedirs_p()
    handler = logging.FileHandler(log_folder / 'airship.log')
    log_format = "%(asctime)s %(levelname)s:%(name)s %(message)s"
    handler.setFormatter(logging.Formatter(log_format))
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)


def main(raw_arguments=None):
    load_plugins()
    parser = build_args_parser()
    args = parser.parse_args(raw_arguments or sys.argv[1:])
    airship_home = path(args.airship_home).abspath()
    set_up_logging(airship_home)
    airship_yaml_path = airship_home / 'etc' / 'airship.yaml'
    if airship_yaml_path.isfile():
        with airship_yaml_path.open('rb') as f:
            config = yaml.load(f)
    else:
        config = {}
    config['home'] = airship_home
    airship = Airship(config)
    args.func(airship, args)


if __name__ == '__main__':
    main()
