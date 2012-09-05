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

    def configure(self, site_name):
        port = 80
        cfg_path = self.sites_dir / "{site_name}:{port}".format(**locals())
        cfg_path.write_bytes(SITE_CFG.format(**locals()))
