import json


DEPLOYMENT_CFG = 'deployments.yaml'


class Deployment(object):
    pass


class Sarge(object):

    def __init__(self, home_path):
        self.home_path = home_path
        self.deployments = []
        self._configure()

    def _configure(self):
        with open(self.home_path/DEPLOYMENT_CFG, 'rb') as f:
            for deployment_config in json.load(f):
                depl = Deployment()
                depl.name = deployment_config['name']
                self.deployments.append(depl)
