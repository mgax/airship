import subprocess
from path import path


SITE_CFG = """\
server {{
    server_name {site_name};
    listen {port};

{urlmap_rules}}}
"""


STATIC_URL = """\
    location {url} {{
        alias {path};
    }}
"""


class NginxTek(object):

    def __init__(self, sites_dir):
        self.sites_dir = path(sites_dir)
        self.reload_cmd = ['/usr/sbin/service', 'nginx', 'reload']

    def reload_(self):
        subprocess.check_call(self.reload_cmd)

    def _cfg_path(self, site_name, port):
        return self.sites_dir / "{site_name}:{port}".format(**locals())

    def configure(self, site_name, port, urlmap):
        urlmap_rules = '\n'.join(STATIC_URL.format(**rule) for rule in urlmap)
        cfg_path = self._cfg_path(site_name, port)
        cfg_path.write_bytes(SITE_CFG.format(**locals()))
        self.reload_()

    def delete(self, site_name, port):
        self._cfg_path(site_name, port).unlink()
        self.reload_()

    def build_args_parser(self):
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        configure = subparsers.add_parser('configure')
        configure.set_defaults(func=self.configure)
        configure.add_argument('site_name')
        configure.add_argument('-p', '--port', type=int, default=80)

        delete = subparsers.add_parser('delete')
        delete.set_defaults(func=self.delete)
        delete.add_argument('site_name')
        delete.add_argument('-p', '--port', type=int, default=80)

        return parser

    def main(self, raw_arguments):
        parser = self.build_args_parser()
        args = parser.parse_args(raw_arguments)
        kwargs = dict(args.__dict__)
        func = kwargs.pop('func')
        func(**kwargs)
