HAPROXY_GLOBAL = """\
global
    maxconn 256

defaults
    timeout connect  5000ms
    timeout client  50000ms
    timeout server  50000ms

"""


class Haproxy(object):

    def __init__(self, sarge_home):
        self.sarge_home = sarge_home
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
