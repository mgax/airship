import json
from path import path
from common import SargeTestCase, imp


class VarFolderTest(SargeTestCase):

    def sarge(self):
        return imp('sarge').Sarge({'home': self.tmp,
                                   'plugins': ['sarge:VarFolderPlugin']})

    def configure_and_deploy(self):
        instance = self.sarge().new_instance({
            'services': [
                {'type': 'var-folder', 'name': 'db'},
            ],
        })
        instance.start()
        return instance

    def test_deploy_passes_var_folder_to_deployment(self):
        instance = self.configure_and_deploy()
        cfg_folder = path(instance.folder + '.cfg')
        with (cfg_folder / imp('sarge.core').APP_CFG).open() as f:
            appcfg = json.load(f)
        db_path = self.tmp / 'var' / instance.id_ / 'db'
        self.assertEqual(appcfg['services']['db'], db_path)

    def test_deploy_creates_var_folder(self):
        instance = self.configure_and_deploy()
        db_path = self.tmp / 'var' / instance.id_ / 'db'
        self.assertTrue(db_path.isdir())
