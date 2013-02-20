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
from .routing import Haproxy
from . import deployer


log = logging.getLogger(__name__)


CFG_LINKS_FOLDER = 'active'
YAML_EXT = '.yaml'
RUN_RC_NAME = '.runrc'


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

    @property
    def meta(self):
        return self.config['meta']

    @property
    def port(self):
        return self.config['port']

    def configure(self):
        self.run_folder.makedirs_p()

    def start(self):
        log.info("Activating bucket %r", self.id_)
        self.configure()
        self.airship.daemons.configure_bucket_running(self)
        self.airship.haproxy.configure_bucket(self)

    def stop(self):
        self.airship.haproxy.remove_bucket(self)
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
        self.airship._free_port(self)

    def run(self, command):
        os.chdir(self.folder)
        environ = dict(os.environ)
        environ.update(self.airship.config.get('env') or {})
        environ['PORT'] = str(self.port)
        venv = self.folder / '_virtualenv'
        if venv.isdir():
            environ['PATH'] = ((venv / 'bin') + ':' + environ['PATH'])
        shell_args = ['/bin/bash']
        if command:
            environ['BASH_ENV'] = RUN_RC_NAME
            shell_args += ['-c', command]
        else:
            shell_args += ['--rcfile', RUN_RC_NAME]
        os.execve(shell_args[0], shell_args, environ)


class Airship(object):
    """ The airship object implements most operations performed by airship. It
    acts as container for deployments.
    """

    def __init__(self, config):
        self.home_path = config['home']
        self.config = config
        etc = self.home_path / 'etc'
        etc.mkdir_p()
        self.buckets_db = KV(etc / 'buckets.db', table='bucket')
        self.daemons = Supervisor(etc)
        self.haproxy = Haproxy(self.home_path, config.get('port_map') or {})
        from routing import configuration_update
        configuration_update.connect(self._haproxy_update, self.haproxy)

    @property
    def cfg_links_folder(self):
        folder = self.home_path / CFG_LINKS_FOLDER
        if not folder.isdir():
            folder.makedirs()
        return folder

    def _haproxy_configure_supervisor(self):
        haproxy_program = self.home_path / 'etc' / 'supervisor.d' / 'haproxy'
        haproxy_program.write_text(self.haproxy.supervisord_config(self))

    def initialize(self):
        self.generate_supervisord_configuration()
        self._haproxy_configure_supervisor()

    def _haproxy_update(self, sender, **extra):
        self._haproxy_configure_supervisor()
        self.daemons.ctl(['update'])
        self.daemons.ctl(['restart', 'haproxy'])

    def generate_supervisord_configuration(self):
        self.daemons.configure(self.home_path)

    def _get_bucket_by_id(self, bucket_id):
        config = self.buckets_db[bucket_id]
        return Bucket(bucket_id, self, config)

    def get_bucket(self, name):
        try:
            return self._get_bucket_by_id(name)

        except KeyError:
            for bucket_id in self.buckets_db:
                bucket = self._get_bucket_by_id(bucket_id)
                if name == bucket.meta.get('APPLICATION_NAME'):
                    return bucket

            else:
                raise KeyError

    def _bucket_folder(self, id_):
        return self.home_path / id_

    def _generate_bucket_id(self, id_prefix):
        for c in range(10):
            id_ = id_prefix + random_id()
            try:
                self._bucket_folder(id_).mkdir()
            except OSError:
                continue
            else:
                return id_
        else:
            raise RuntimeError("Failed to generate unique bucket ID")

    def _open_ports_db(self):
        return KV(self.home_path / 'etc' / 'buckets.db', table='port')

    def _allocate_port(self, bucket_id):
        from itertools import chain
        port_range = self.config.get('port_range', [5000, 5099])
        start_port = port_range[0]
        end_port = port_range[1] + 1

        ports_db = self._open_ports_db()
        with ports_db.lock():
            next_port = ports_db.get('next', start_port)
            if start_port <= next_port <= end_port:
                queue = chain(xrange(next_port, end_port),
                              xrange(start_port, next_port - 1))
            else:
                queue = xrange(start_port, end_port)
            for port in queue:
                assert start_port <= port <= end_port
                if port not in ports_db:
                    ports_db[port] = bucket_id
                    ports_db['next'] = port + 1
                    return port
            else:
                raise RuntimeError("No ports free to allocate")

    def _free_port(self, bucket):
        ports_db = self._open_ports_db()
        port = ports_db.pop(bucket.port, None)
        if port is not None:
            assert port == bucket.id_

    def new_bucket(self, config={}):
        meta = {'CREATION_TIME': datetime.utcnow().isoformat()}
        app_name = config.get('application_name')
        if app_name:
            meta['APPLICATION_NAME'] = app_name
            id_prefix = app_name + '-'
        else:
            id_prefix = ''
        bucket_id = self._generate_bucket_id(id_prefix)
        self.buckets_db[bucket_id] = {
            'require-services': config.get('services', {}),
            'urlmap': config.get('urlmap', []),
            'meta': meta,
            'port': self._allocate_port(bucket_id),
        }
        bucket = self._get_bucket_by_id(bucket_id)
        return bucket

    def list_buckets(self):
        buckets = []
        for bucket_id in self.buckets_db:
            bucket = self._get_bucket_by_id(bucket_id)
            buckets.append({
                'id': bucket.id_,
                'meta': bucket.meta,
                'port': bucket.port,
            })
        return {'buckets': buckets}


def load_plugins():
    for entry_point in pkg_resources.iter_entry_points('sarge_plugins'):
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
            f.write('{"port_range": [5000, 5100]}\n')
    (airship.home_path / 'var').mkdir_p()
    (airship.home_path / 'var' / 'log').mkdir_p()
    (airship.home_path / 'var' / 'run').mkdir_p()
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
        deployer.deploy(airship, args.tarfile, args.procname)
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
    deploy_parser.add_argument('procname')
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
