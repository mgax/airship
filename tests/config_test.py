from utils import unittest
import tempfile
import json
from path import path
from mock import patch
from utils import configure_sarge, configure_deployment, username


def setUpModule(self):
    import sarge; self.sarge = sarge
    self._subprocess_patch = patch('sarge.subprocess')
    self.mock_subprocess = self._subprocess_patch.start()


def tearDownModule(self):
    self._subprocess_patch.stop()


class DeploymentTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)
        configure_sarge(self.tmp, {})

    def test_enumerate_deployments(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])

    def test_ignore_non_yaml_files(self):
        configure_deployment(self.tmp, {'name': 'testy', 'user': username})
        cfgdir = self.tmp/sarge.DEPLOYMENT_CFG_DIR
        (cfgdir/'garbage').write_text('{}')
        self.assertItemsEqual([f.name for f in cfgdir.listdir()],
                              ['testy.yaml', 'garbage'])
        s = sarge.Sarge(self.tmp)
        self.assertEqual([d.name for d in s.deployments], ['testy'])

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
        s = sarge.Sarge(self.tmp)
        testy = s.get_deployment('testy')
        version_folder = testy.new_version()
        cfg_folder = path(version_folder + '.cfg')
        testy.activate_version(version_folder)
        with (cfg_folder/sarge.APP_CFG).open() as f:
            appcfg = json.load(f)
        self.assertIn({'name': 'zefolder',
                       'type': 'persistent-folder',
                       'path': zefolder_path},
                      appcfg['services'])
