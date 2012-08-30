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
        appcfg = instance.get_appcfg()
        tmp_path = self.tmp / 'var' / 'tmp'
        self.assertEqual(path(appcfg['VOLATILE_PATH']).parent, tmp_path)

    def test_deploy_creates_var_folder(self):
        self.configure_and_deploy()
        tmp_path = self.tmp / 'var' / 'tmp'
        self.assertTrue(len(tmp_path.listdir()), 1)

    def test_deploy_passes_persistent_folder_to_deployment(self):
        instance = self.configure_and_deploy()
        appcfg = instance.get_appcfg()
        db_path = self.tmp / 'var' / 'data' / 'db'
        self.assertEqual(appcfg['DB_PATH'], db_path)

    def test_deploy_creates_persistent_folder(self):
        self.configure_and_deploy()
        db_path = self.tmp / 'var' / 'data' / 'db'
        self.assertTrue(db_path.isdir())


class ListenPluginTest(SargeTestCase):

    def sarge(self):
        return imp('sarge').Sarge({
            'home': self.tmp,
            'plugins': ['sarge:ListenPlugin']})

    def configure_and_start(self, cfg):
        instance = self.sarge().new_instance(cfg)
        instance.start()
        return instance

    def test_listen_host_is_found_in_appcfg(self):
        instance = self.configure_and_start({
            'services': {'listen': {'type': 'listen', 'host': '127.0.0.1'}}})
        self.assertEqual(instance.get_appcfg()['LISTEN_HOST'], '127.0.0.1')

    def test_listen_port_is_found_in_appcfg(self):
        instance = self.configure_and_start({
            'services': {'listen': {'type': 'listen', 'port': '4327'}}})
        self.assertEqual(instance.get_appcfg()['LISTEN_PORT'], '4327')

    def test_listen_random_port_is_found_in_appcfg(self):
        instance = self.configure_and_start({
            'services': {'listen': {'type': 'listen', 'port': 'random'}}})
        appcfg = instance.get_appcfg()
        self.assertIn('LISTEN_PORT', appcfg)
        self.assertTrue(1024 <= int(appcfg['LISTEN_PORT']) < 65536)
