import json
from path import path
from mock import patch
from common import configure_sarge, configure_deployment, username, imp
from common import SargeTestCase


class DeploymentTest(SargeTestCase):

    def setUp(self):
        configure_sarge(self.tmp, {})

    def test_enumerate_deployments(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        self.assertEqual([d.name for d in self.sarge().deployments], ['testy'])

    def test_ignore_non_yaml_files(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        cfgdir = self.tmp / imp('sarge').DEPLOYMENT_CFG_DIR
        (cfgdir / 'garbage').write_text('{}')
        self.assertItemsEqual([f.name for f in cfgdir.listdir()],
                              ['testy.yaml', 'garbage'])
        self.assertEqual([d.name for d in self.sarge().deployments], ['testy'])

    def test_hardcoded_service_is_passed_to_app(self):
        zefolder_path = self.tmp/'zefolder'
        configure_deployment(self.tmp, {
            'name': 'testy',
            'user': username,
            'services': [
                {'name': 'zefolder',
                 'type': 'persistent-folder',
                 'path': zefolder_path},
            ],
        })
        testy = self.sarge().get_deployment('testy')
        version_folder = testy.new_version()
        cfg_folder = path(version_folder + '.cfg')
        testy.activate_version(version_folder)
        with (cfg_folder / imp('sarge').APP_CFG).open() as f:
            appcfg = json.load(f)
        self.assertEqual(appcfg['services']['zefolder'], {
            'name': 'zefolder',
            'type': 'persistent-folder',
            'path': zefolder_path})
