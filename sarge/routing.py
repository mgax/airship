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
    bind *:{stable_port}
    server {proc_name}1 127.0.0.1:{port} maxconn 32
"""


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
        (self.etc_haproxy / 'bits').makedirs()
        (self.etc_haproxy / 'bits' / '0-global').write_text(HAPROXY_GLOBAL)
        (self.etc_haproxy / 'haproxy.cfg').write_text(HAPROXY_GLOBAL)

    def configure_instance(self, instance):
        proc_name = instance.meta.get('APPLICATION_NAME')
        if proc_name not in self.port_map:
            return
        port = instance.port
        stable_port = self.port_map[proc_name]
        haproxy_route_cfg = HAPROXY_ROUTE.format(**locals())
        (self.etc_haproxy / 'bits' / proc_name).write_text(haproxy_route_cfg)
        self.update_haproxy()

    def remove_instance(self, instance):
        proc_name = instance.meta.get('APPLICATION_NAME')
        if proc_name not in self.port_map:
            return
        bit_file = self.etc_haproxy / 'bits' / proc_name
        if bit_file.isfile():
            bit_file.unlink()
            self.update_haproxy()

    def update_haproxy(self):
        bits = self.etc_haproxy / 'bits'
        haproxy_cfg = '\n'.join(f.text() for f in sorted(bits.listdir()))
        (self.etc_haproxy / 'haproxy.cfg').write_text(haproxy_cfg)
        # TODO restart haproxy process
