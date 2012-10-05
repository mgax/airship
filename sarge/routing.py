import blinker


configuration_update = blinker.Signal()

SUPERVISORD_HAPROXY = """\
[program:haproxy]
redirect_stderr = true
stdout_logfile = {sarge_home}/var/log/haproxy.log
startsecs = 0
startretries = 1
autostart = true
command = /usr/sbin/haproxy -f {sarge_home}/etc/haproxy/haproxy.cfg
"""


HAPROXY_GLOBAL = """\
global
    maxconn 256

defaults
    timeout connect  5000ms
    timeout client  50000ms
    timeout server  50000ms
"""


HAPROXY_ROUTE = """\
listen {proc_name}
    bind 127.0.0.1:{stable_port}
    server {proc_name}1 127.0.0.1:{port} maxconn 32
"""


HAPROXY_FRAGMENTS = 'fragments'


class Haproxy(object):

    def __init__(self, sarge_home, port_map):
        self.sarge_home = sarge_home
        self.port_map = port_map
        self._initialize()

    @property
    def etc_haproxy(self):
        return self.sarge_home / 'etc' / 'haproxy'

    def _initialize(self):
        if self.etc_haproxy.isdir():
            return
        (self.etc_haproxy / HAPROXY_FRAGMENTS).makedirs()
        (self.etc_haproxy / HAPROXY_FRAGMENTS / '0-global').write_text(HAPROXY_GLOBAL)
        (self.etc_haproxy / 'haproxy.cfg').write_text(HAPROXY_GLOBAL)

    def supervisord_config(self):
        return SUPERVISORD_HAPROXY.format(sarge_home=self.sarge_home)

    def configure_instance(self, instance):
        proc_name = instance.meta.get('APPLICATION_NAME')
        if proc_name not in self.port_map:
            return
        port = instance.port
        stable_port = self.port_map[proc_name]
        haproxy_route_cfg = HAPROXY_ROUTE.format(**locals())
        (self.etc_haproxy / HAPROXY_FRAGMENTS / proc_name).write_text(haproxy_route_cfg)
        self.update_haproxy()

    def remove_instance(self, instance):
        proc_name = instance.meta.get('APPLICATION_NAME')
        if proc_name not in self.port_map:
            return
        bit_file = self.etc_haproxy / HAPROXY_FRAGMENTS / proc_name
        if bit_file.isfile():
            bit_file.unlink()
            self.update_haproxy()

    def update_haproxy(self):
        bits = self.etc_haproxy / HAPROXY_FRAGMENTS
        haproxy_cfg = '\n'.join(f.text() for f in sorted(bits.listdir()))
        (self.etc_haproxy / 'haproxy.cfg').write_text(haproxy_cfg)
        configuration_update.send(self)
