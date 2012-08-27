import tempfile
from StringIO import StringIO
import json
from path import path
from mock import Mock, patch, call
from common import SargeTestCase, imp


class ShellTest(SargeTestCase):

    def setUp(self):
        (self.tmp / 'etc' / 'sarge.yaml').write_text('{}')

    @patch('sarge.core.Sarge.new_instance')
    def test_new_instance_calls_api_and_returns_path(self, new_instance):
        new_instance.return_value = Mock(folder="path-to-new-version")
        with patch('sys.stdout', StringIO()) as stdout:
            config = json.dumps({'hello': "world"})
            imp('sarge.core').main([str(self.tmp), 'new_instance', config])
        self.assertEqual(new_instance.mock_calls, [call({'hello': "world"})])
        self.assertEqual(stdout.getvalue().strip(), "path-to-new-version")

    @patch('sarge.core.Instance.start')
    def test_start_instance_calls_api_method(self, start):
        instance = self.sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'start_instance', instance.id_])
        self.assertEqual(start.mock_calls, [call()])

    @patch('sarge.core.Instance.stop')
    def test_stop_instance_calls_api_method(self, stop):
        instance = self.sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'stop_instance', instance.id_])
        self.assertEqual(stop.mock_calls, [call()])

    @patch('sarge.core.Instance.destroy')
    def test_destroy_instance_calls_api_method(self, destroy):
        instance = self.sarge().new_instance()
        imp('sarge.core').main([str(self.tmp),
                                'destroy_instance', instance.id_])
        self.assertEqual(destroy.mock_calls, [call()])

    def test_init_creates_configuration(self):
        other_tmp = path(tempfile.mkdtemp())
        (other_tmp / 'etc').mkdir()
        self.addCleanup(other_tmp.rmtree)
        (other_tmp / 'etc' / 'sarge.yaml').write_text('{}')

        core = imp('sarge.core')
        core.main([str(other_tmp), 'init'])
        expected = [core.DEPLOYMENT_CFG_DIR, 'etc', 'var']
        self.assertItemsEqual([f.name for f in other_tmp.listdir()], expected)
        self.assertTrue((other_tmp / core.DEPLOYMENT_CFG_DIR).isdir())
