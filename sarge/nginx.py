import logging
from string import Template
from . import signals


log = logging.getLogger(__name__)


def interpolate_config(raw_entry, appcfg):
    def interpolate(value):
        return Template(value).substitute(appcfg)
    return dict((k, interpolate(v)) for k, v in raw_entry.iteritems())


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
        '    alias %(instance_folder)s/%(path)s;\n'
        '}\n')

    PHP_TEMPLATE = (
        'location %(url)s {\n'
        '    include %(fcgi_params_path)s;\n'
        '    fastcgi_param SCRIPT_FILENAME '
                '%(instance_folder)s$fastcgi_script_name;\n'
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
        signals.instance_will_start.connect(self.activate_deployment, sarge)
        signals.sarge_initializing.connect(self.initialize, sarge)
        signals.instance_has_stopped.connect(self.instance_stop, sarge)

    fcgi_params_path = '/etc/nginx/fastcgi_params'

    @property
    def etc_nginx(self):
        return self.sarge.home_path / 'etc' / 'nginx'

    def initialize(self, sarge):
        if not self.etc_nginx.isdir():
            (self.etc_nginx).makedirs()
        sarge_sites_conf = self.etc_nginx / 'sarge_sites.conf'
        if not sarge_sites_conf.isfile():
            log.debug("Writing \"sarge_sites\" "
                      "nginx configuration at %r.",
                      sarge_sites_conf)
            sarge_sites_conf.write_text('include %s/*;\n' % self.etc_nginx)
        self.etc_nginx.makedirs_p()

    def _conf_site_path(self, instance):
        return self.etc_nginx / (instance.id_ + '-site')

    def _conf_urlmap_path(self, instance):
        return self.etc_nginx / (instance.id_ + '-urlmap')

    def activate_deployment(self, sarge, instance, appcfg, **extra):
        conf_path = self._conf_site_path(instance)
        urlmap_path = self._conf_urlmap_path(instance)

        log.debug("Writing nginx configuration for instance %r at %r.",
                  instance.id_, conf_path)

        conf_options = ""
        nginx_options = instance.config.get('nginx_options', {})
        for key, value in sorted(nginx_options.items()):
            conf_options += '  %s %s;\n' % (key, value)

        conf_urlmap = ""

        for raw_entry in instance.config.get('urlmap', []):
            log.debug("urlmap entry: %r", raw_entry)

            entry = interpolate_config(raw_entry, appcfg)

            if entry['type'] == 'static':
                conf_urlmap += self.STATIC_TEMPLATE % dict(entry,
                        instance_folder=instance.folder)
            elif entry['type'] == 'wsgi':
                socket_path = instance.run_folder / 'wsgi-app.sock'
                conf_urlmap += self.WSGI_TEMPLATE % dict(entry,
                        socket_path=socket_path,
                        fcgi_params_path=self.fcgi_params_path)
                instance.config['tmp-wsgi-app'] = entry['app_factory']

            elif entry['type'] == 'php':
                socket_path = instance.run_folder / 'php.sock'
                conf_urlmap += self.PHP_TEMPLATE % dict(entry,
                        socket_path=socket_path,
                        instance_folder=instance.folder,
                        fcgi_params_path=self.fcgi_params_path)

                server_script = instance.folder / 'server'
                with server_script.open('wb') as f:
                    f.write("#!/bin/sh\n\n"
                            "/usr/bin/spawn-fcgi -s %(socket_path)s -M 0777 "
                              "-f /usr/bin/php5-cgi -n\n"
                            % {'socket_path': socket_path})
                server_script.chmod(0755)

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

    def instance_stop(self, sarge, instance, **extra):
        self._conf_site_path(instance).unlink()
        self._conf_urlmap_path(instance).unlink()
