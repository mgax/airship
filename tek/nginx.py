import subprocess
import errno
from path import path
try:
    import simplejson as json
except ImportError:
    import json


SITE_CFG = """\
server {{
{option_lines}

{urlmap_rules}}}
"""


STATIC_URL = """\
    location {url} {{
        alias {path};
    }}
"""


FCGI_URL = """\
    location {url} {{
        include /etc/nginx/fastcgi_params;
        fastcgi_param PATH_INFO $fastcgi_script_name;
        fastcgi_param SCRIPT_NAME "";
        fastcgi_pass {socket};
    }}
"""


PROXY_URL = """\
    location {url} {{
        proxy_pass {upstream_url};
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
"""


URL_TEMPLATE = {
    'static': STATIC_URL,
    'fcgi': FCGI_URL,
    'proxy': PROXY_URL,
}


class NginxTek(object):

    def __init__(self, sites_dir):
        self.sites_dir = path(sites_dir)
        self.reload_cmd = ['/usr/sbin/service', 'nginx', 'reload']

    def reload_(self):
        subprocess.check_call(self.reload_cmd)

    def _cfg_path(self, site_name):
        return self.sites_dir / site_name

    def configure(self, site_name, config):
        (server_name, port) = site_name.split(':')
        options = {
            'server_name': server_name,
            'listen': port,
        }
        options.update(config.get('options', {}))
        option_lines = '\n'.join("    {0} {1};".format(name, options[name])
                                 for name in sorted(options))
        urlmap_rules = '\n'.join(URL_TEMPLATE[rule['type']].format(**rule)
                                 for rule in config.get('urlmap', []))
        cfg_path = self._cfg_path(site_name)
        cfg_path.write_bytes(SITE_CFG.format(**locals()))
        self.reload_()

    def delete(self, site_name, nofail=False):
        try:
            self._cfg_path(site_name).unlink()
        except OSError, e:
            if nofail and e.errno == errno.ENOENT:
                return
            raise
        self.reload_()

    def build_args_parser(self):
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        configure = subparsers.add_parser('configure')
        configure.set_defaults(func=self.configure)
        configure.add_argument('site_name')
        configure.add_argument('config')

        delete = subparsers.add_parser('delete')
        delete.set_defaults(func=self.delete)
        delete.add_argument('site_name')
        delete.add_argument('-f', '--nofail', action='store_true')

        return parser

    def main(self, raw_arguments):
        parser = self.build_args_parser()
        args = parser.parse_args(raw_arguments)
        kwargs = dict(args.__dict__)
        func = kwargs.pop('func')
        if 'config' in kwargs:
            kwargs['config'] = json.loads(kwargs['config'])
        func(**kwargs)
