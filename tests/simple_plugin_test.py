import json
from path import path
from common import SargeTestCase, imp


class VarFolderTest(SargeTestCase):

    def sarge(self):
        return imp('sarge').Sarge({'home': self.tmp,
                                   'plugins': ['sarge:VarFolderPlugin']})

    def configure_instance(self):
        instance = self.sarge().new_instance({
            'services': {
                'volatile': {'type': 'var-folder'},
                'db': {'type': 'persistent-folder'},
            },
        })
        instance.configure()
        return instance

    def test_deploy_passes_var_folder_to_deployment(self):
        instance = self.configure_instance()
        appcfg = instance.get_appcfg()
        tmp_path = self.tmp / 'var' / 'tmp'
        self.assertEqual(path(appcfg['VOLATILE_PATH']).parent, tmp_path)

    def test_deploy_creates_var_folder(self):
        self.configure_instance()
        tmp_path = self.tmp / 'var' / 'tmp'
        self.assertTrue(len(tmp_path.listdir()), 1)

    def test_deploy_passes_persistent_folder_to_deployment(self):
        instance = self.configure_instance()
        appcfg = instance.get_appcfg()
        db_path = self.tmp / 'var' / 'data' / 'db'
        self.assertEqual(appcfg['DB_PATH'], db_path)

    def test_deploy_creates_persistent_folder(self):
        self.configure_instance()
        db_path = self.tmp / 'var' / 'data' / 'db'
        self.assertTrue(db_path.isdir())


class ListenPluginTest(SargeTestCase):

    def sarge(self):
        return imp('sarge').Sarge({
            'home': self.tmp,
            'plugins': ['sarge:ListenPlugin']})

    def configure_instance(self, cfg):
        instance = self.sarge().new_instance(cfg)
        instance.configure()
        return instance

    def test_listen_host_is_found_in_appcfg(self):
        instance = self.configure_instance({
            'services': {'listen': {'type': 'listen', 'host': '127.0.0.1'}}})
        self.assertEqual(instance.get_appcfg()['LISTEN_HOST'], '127.0.0.1')

    def test_listen_port_is_found_in_appcfg(self):
        instance = self.configure_instance({
            'services': {'listen': {'type': 'listen', 'port': '4327'}}})
        self.assertEqual(instance.get_appcfg()['LISTEN_PORT'], '4327')
