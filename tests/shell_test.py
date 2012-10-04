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
        new_instance.return_value = Mock(id_="instance-id")
        with patch('sys.stdout', StringIO()) as stdout:
            config = json.dumps({'hello': "world"})
            imp('sarge.core').main([str(self.tmp), 'new', config])
        self.assertEqual(new_instance.mock_calls, [call({'hello': "world"})])
        self.assertEqual(stdout.getvalue().strip(), "instance-id")

    @patch('sarge.core.Instance.configure')
    def test_configure_instance_calls_api_method(self, configure):
        instance = self.create_sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'configure', instance.id_])
        self.assertEqual(configure.mock_calls, [call()])

    @patch('sarge.core.Instance.start')
    def test_start_instance_calls_api_method(self, start):
        instance = self.create_sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'start', instance.id_])
        self.assertEqual(start.mock_calls, [call()])

    @patch('sarge.core.Instance.stop')
    def test_stop_instance_calls_api_method(self, stop):
        instance = self.create_sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'stop', instance.id_])
        self.assertEqual(stop.mock_calls, [call()])

    @patch('sarge.core.Instance.trigger')
    def test_trigger_instance_calls_api_method(self, trigger):
        instance = self.create_sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'trigger', instance.id_])
        self.assertEqual(trigger.mock_calls, [call()])

    @patch('sarge.core.Instance.destroy')
    def test_destroy_instance_calls_api_method(self, destroy):
        instance = self.create_sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'destroy', instance.id_])
        self.assertEqual(destroy.mock_calls, [call()])

    @patch('sarge.core.Instance.run')
    def test_run_instance_calls_api_method_with_args(self, run):
        instance = self.create_sarge().new_instance()
        imp('sarge.core').main([str(self.tmp), 'run', instance.id_, 'a'])
        self.assertEqual(run.mock_calls, [call('a')])

    @patch('sarge.core.Sarge.list_instances')
    def test_destroy_instance_calls_api_method(self, list_instances):
        data = {'some': ['json', 'data']}
        list_instances.return_value = data
        with patch('sys.stdout', StringIO()) as stdout:
            config = json.dumps({'hello': "world"})
            imp('sarge.core').main([str(self.tmp), 'list'])
        self.assertEqual(list_instances.mock_calls, [call()])
        self.assertEqual(json.loads(stdout.getvalue()), data)

    def test_init_creates_configuration_and_bin_scripts(self):
        other_tmp = path(tempfile.mkdtemp())
        self.addCleanup(other_tmp.rmtree)

        core = imp('sarge.core')
        core.main([str(other_tmp), 'init'])
        expected = [core.DEPLOYMENT_CFG_DIR, 'bin', 'etc', 'var']
        self.assertItemsEqual([f.name for f in other_tmp.listdir()], expected)
        self.assertItemsEqual([f.name for f in (other_tmp / 'bin').listdir()],
                              ['sarge', 'supervisord', 'supervisorctl'])
        self.assertTrue((other_tmp / core.DEPLOYMENT_CFG_DIR).isdir())
        sarge_yaml_path = other_tmp / 'etc' / 'sarge.yaml'
        self.assertTrue(sarge_yaml_path.isfile())
        self.assertEqual(json.loads(sarge_yaml_path.text()), {})
