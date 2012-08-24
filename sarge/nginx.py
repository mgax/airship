import logging
import yaml
from path import path
from .util import ensure_folder, force_symlink
import subprocess


log = logging.getLogger(__name__)


class NginxPlugin(object):
    """ Generates a configuration file for each deployment based on its urlmap.
    Upon activation of a new deployment version, the new nginx configuration is
    written, and nginx is reloaded. """

    WSGI_TEMPLATE = (
        'location %(url)s {\n'
        '    include %(fcgi_params_path)s;\n'
        '    fastcgi_param PATH_INFO $fastcgi_script_name;\n'
        '    fastcgi_param SCRIPT_NAME "";\n'
        '    fastcgi_pass unix:%(socket_path)s;\n'
        '}\n')

    STATIC_TEMPLATE = (
        'location %(url)s {\n'
        '    alias %(version_folder)s/%(path)s;\n'
        '}\n')

    PHP_TEMPLATE = (
        'location %(url)s {\n'
        '    include %(fcgi_params_path)s;\n'
        '    fastcgi_param SCRIPT_FILENAME '
                '%(version_folder)s$fastcgi_script_name;\n'
        '    fastcgi_param PATH_INFO $fastcgi_script_name;\n'
        '    fastcgi_param SCRIPT_NAME "";\n'
        '    fastcgi_pass unix:%(socket_path)s;\n'
        '}\n')

    FCGI_TEMPLATE = (
        'location %(url)s {\n'
        '    include %(fcgi_params_path)s;\n'
        '    fastcgi_param PATH_INFO $fastcgi_script_name;\n'
        '    fastcgi_param SCRIPT_NAME "";\n'
        '    fastcgi_pass %(socket)s;\n'
        '}\n')

    PROXY_TEMPLATE = (
        'location %(url)s {\n'
        '    proxy_pass %(upstream_url)s;\n'
        '    proxy_redirect off;\n'
        '    proxy_set_header Host $host;\n'
        '    proxy_set_header X-Real-IP $remote_addr;\n'
        '    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n'
        '}\n')

    def __init__(self, sarge):
        self.sarge = sarge
        sarge.on_instance_start.connect(self.activate_deployment, weak=False)
        sarge.on_initialize.connect(self.initialize, weak=False)

    fcgi_params_path = '/etc/nginx/fastcgi_params'

    FOLDER_NAME = 'nginx.plugin'

    @property
    def folder(self):
        return self.sarge.home_path / self.FOLDER_NAME

    @property
    def sites_folder(self):
        return self.folder / 'sites'

    def initialize(self, sarge):
        if not self.sites_folder.isdir():
            (self.sites_folder).makedirs()

    def activate_deployment(self, instance, share, **extra):
        version_folder = instance.folder
        run_folder = path(instance.folder + '.run')
        cfg_folder = path(instance.folder + '.cfg')

        app_config_path = version_folder / 'sargeapp.yaml'
        if app_config_path.exists():
            with open(app_config_path, 'rb') as f:
                app_config = yaml.load(f)
        else:
            app_config = {}

        conf_path = cfg_folder / 'nginx-site.conf'
        urlmap_path = cfg_folder / 'nginx-urlmap.conf'

        log.debug("Writing nginx configuration for instance %r at %r.",
                  instance.id_, conf_path)

        conf_options = ""
        nginx_options = instance.config.get('nginx_options', {})
        for key, value in sorted(nginx_options.items()):
            conf_options += '  %s %s;\n' % (key, value)

        conf_urlmap = ""

        for entry in app_config.get('urlmap', []):
            log.debug("urlmap entry: %r", entry)

            if entry['type'] == 'static':
                conf_urlmap += self.STATIC_TEMPLATE % dict(entry,
                        version_folder=version_folder)
            elif entry['type'] == 'wsgi':
                socket_path = run_folder / 'wsgi-app.sock'
                conf_urlmap += self.WSGI_TEMPLATE % dict(entry,
                        socket_path=socket_path,
                        fcgi_params_path=self.fcgi_params_path)
                instance.config['tmp-wsgi-app'] = entry['app_factory']

            elif entry['type'] == 'php':
                socket_path = run_folder / 'php.sock'
                conf_urlmap += self.PHP_TEMPLATE % dict(entry,
                        socket_path=socket_path,
                        version_folder=version_folder,
                        fcgi_params_path=self.fcgi_params_path)

                share['programs'].append({
                    'name': 'fcgi_php',
                    'command': (
                        '/usr/bin/spawn-fcgi -s %(socket_path)s -M 0777 '
                        '-f /usr/bin/php5-cgi -n'
                        % {'socket_path': socket_path})
                })

            elif entry['type'] == 'fcgi':
                socket_uri = entry['socket']
                if socket_uri.startswith('tcp://'):
                    socket = socket_uri[len('tcp://'):]
                elif socket_uri.startswith('unix:///'):
                    socket = 'unix:' + socket_uri[len('unix://'):]
                else:
                    raise ValueError("Can't parse socket %r" % socket_uri)
                conf_urlmap += self.FCGI_TEMPLATE % dict(entry,
                        socket=socket,
                        fcgi_params_path=self.fcgi_params_path)

            elif entry['type'] == 'proxy':
                conf_urlmap += self.PROXY_TEMPLATE % entry

            else:
                raise NotImplementedError

        with open(conf_path, 'wb') as f:
            f.write('server {\n')
            f.write(conf_options)
            f.write('  include %s;\n' % urlmap_path)
            f.write('}\n')

        with open(urlmap_path, 'wb') as f:
            f.write(conf_urlmap)

        ensure_folder(self.sites_folder)
        force_symlink(conf_path, self.sites_folder / instance.id_)
