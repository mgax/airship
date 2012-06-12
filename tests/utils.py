import json


def configure_deployment(sarge_home, config):
    import sarge
    deployment_config_folder = sarge_home/sarge.DEPLOYMENT_CFG_DIR
    deployment_config_folder.makedirs()
    filename = config['name'] + '.yaml'
    with open(deployment_config_folder/filename, 'wb') as f:
        json.dump(config, f)
