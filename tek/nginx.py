from path import path


SITE_CFG = """\
server {{
    server_name {site_name};
    listen {port};
}}
"""


class NginxTek(object):

    def __init__(self, sites_dir):
        self.sites_dir = sites_dir

    def reload_(self):
        raise NotImplementedError

    def _cfg_path(self, site_name, port):
        return self.sites_dir / "{site_name}:{port}".format(**locals())

    def configure(self, site_name):
        port = 80
        cfg_path = self._cfg_path(site_name, port)
        cfg_path.write_bytes(SITE_CFG.format(**locals()))
        self.reload_()

    def delete(self, site_name):
        self._cfg_path(site_name, 80).unlink()
        self.reload_()
