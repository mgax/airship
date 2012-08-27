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
        with instance.appcfg_path.open() as f:
            appcfg = json.load(f)
        tmp_path = self.tmp / 'var' / 'tmp'
        self.assertEqual(path(appcfg['VOLATILE_PATH']).parent, tmp_path)

    def test_deploy_creates_var_folder(self):
        instance = self.configure_and_deploy()
        tmp_path = self.tmp / 'var' / 'tmp'
        self.assertTrue(len(tmp_path.listdir()), 1)

    def test_deploy_passes_persistent_folder_to_deployment(self):
        instance = self.configure_and_deploy()
        with instance.appcfg_path.open() as f:
            appcfg = json.load(f)
        db_path = self.tmp / 'var' / 'data' / 'db'
        self.assertEqual(appcfg['DB_PATH'], db_path)

    def test_deploy_creates_persistent_folder(self):
        instance = self.configure_and_deploy()
        db_path = self.tmp / 'var' / 'data' / 'db'
        self.assertTrue(db_path.isdir())
