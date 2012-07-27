import json
from path import path
from common import configure_deployment, configure_sarge, username, imp
from common import SargeTestCase


class VarFolderTest(SargeTestCase):

    def setUp(self):
        configure_sarge(self.tmp, {'plugins': ['sarge:VarFolderPlugin']})

    def configure_and_deploy(self):
        configure_deployment(self.tmp, {
            'name': 'testy',
            'user': username,
            'require-services': [
                {'type': 'var-folder', 'name': 'db'},
            ],
        })
        testy = self.sarge().get_deployment('testy')
        version_folder = testy.new_version()
        testy.activate_version(version_folder)
        return version_folder

    def test_deploy_passes_var_folder_to_deployment(self):
        version_folder = self.configure_and_deploy()
        cfg_folder = path(version_folder + '.cfg')
        with (cfg_folder / imp('sarge.core').APP_CFG).open() as f:
            appcfg = json.load(f)
        db_path = self.tmp / 'var' / 'testy' / 'db'
        self.assertEqual(appcfg['services']['db'], db_path)

    def test_deploy_creates_var_folder(self):
        self.configure_and_deploy()
        db_path = self.tmp / 'var' / 'testy' / 'db'
        self.assertTrue(db_path.isdir())
