import json
from path import path
from common import SargeTestCase, imp


class VarFolderTest(SargeTestCase):

    def sarge(self):
        return imp('sarge').Sarge({'home': self.tmp,
                                   'plugins': ['sarge:VarFolderPlugin']})

    def configure_and_deploy(self):
        instance = self.sarge().new_instance({
            'services': {
                'volatile': {'type': 'var-folder'},
                'db': {'type': 'persistent-folder'},
            },
        })
        instance.start()
        return instance

    def test_deploy_passes_var_folder_to_deployment(self):
        instance = self.configure_and_deploy()
        cfg_folder = path(instance.folder + '.cfg')
        with (cfg_folder / imp('sarge.core').APP_CFG).open() as f:
            appcfg = json.load(f)
        volatile_path = self.tmp / 'var' / instance.id_ / 'volatile'
        self.assertEqual(appcfg['services']['volatile'], volatile_path)

    def test_deploy_creates_var_folder(self):
        instance = self.configure_and_deploy()
        volatile_path = self.tmp / 'var' / instance.id_ / 'volatile'
        self.assertTrue(volatile_path.isdir())

    def test_deploy_passes_persistent_folder_to_deployment(self):
        instance = self.configure_and_deploy()
        cfg_folder = path(instance.folder + '.cfg')
        with (cfg_folder / imp('sarge.core').APP_CFG).open() as f:
            appcfg = json.load(f)
        db_path = self.tmp / 'var' / 'db'
        self.assertEqual(appcfg['services']['db'], db_path)

    def test_deploy_creates_persistent_folder(self):
        instance = self.configure_and_deploy()
        db_path = self.tmp / 'var' / 'db'
        self.assertTrue(db_path.isdir())
