import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest


def configure_sarge(sarge_home, config):
    import sarge
    with open(sarge_home/sarge.DEPLOYMENT_CFG, 'wb') as f:
        json.dump(config, f)


def configure_deployment(sarge_home, config):
    import sarge
    deployment_config_folder = sarge_home/sarge.DEPLOYMENT_CFG_DIR
    sarge.ensure_folder(deployment_config_folder)
    filename = config['name'] + '.yaml'
    with open(deployment_config_folder/filename, 'wb') as f:
        json.dump(config, f)
