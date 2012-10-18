import tempfile
from StringIO import StringIO
import json
from path import path
from mock import Mock, patch, call
from common import SargeTestCase, imp


class ShellTest(SargeTestCase):

    def setUp(self):
        (self.tmp / 'etc' / 'sarge.yaml').write_text('{}')

    @patch('sarge.core.Sarge.new_bucket')
    def test_new_bucket_calls_api_and_returns_path(self, new_bucket):
        new_bucket.return_value = Mock(id_="bucket-id")
        with patch('sys.stdout', StringIO()) as stdout:
            config = json.dumps({'hello': "world"})
            imp('sarge.core').main([str(self.tmp), 'new', config])
        self.assertEqual(new_bucket.mock_calls, [call({'hello': "world"})])
        self.assertEqual(stdout.getvalue().strip(), "bucket-id")

    @patch('sarge.core.Bucket.configure')
    def test_configure_bucket_calls_api_method(self, configure):
        bucket = self.create_sarge().new_bucket()
        imp('sarge.core').main([str(self.tmp), 'configure', bucket.id_])
        self.assertEqual(configure.mock_calls, [call()])

    @patch('sarge.core.Bucket.start')
    def test_start_bucket_calls_api_method(self, start):
        bucket = self.create_sarge().new_bucket()
        imp('sarge.core').main([str(self.tmp), 'start', bucket.id_])
        self.assertEqual(start.mock_calls, [call()])

    @patch('sarge.core.Bucket.stop')
    def test_stop_bucket_calls_api_method(self, stop):
        bucket = self.create_sarge().new_bucket()
        imp('sarge.core').main([str(self.tmp), 'stop', bucket.id_])
        self.assertEqual(stop.mock_calls, [call()])

    @patch('sarge.core.Bucket.trigger')
    def test_trigger_bucket_calls_api_method(self, trigger):
        bucket = self.create_sarge().new_bucket()
        imp('sarge.core').main([str(self.tmp), 'trigger', bucket.id_])
        self.assertEqual(trigger.mock_calls, [call()])

    @patch('sarge.core.Bucket.destroy')
    def test_destroy_bucket_calls_api_method(self, destroy):
        bucket = self.create_sarge().new_bucket()
        imp('sarge.core').main([str(self.tmp), 'destroy', bucket.id_])
        self.assertEqual(destroy.mock_calls, [call()])

    @patch('sarge.core.Bucket.run')
    def test_run_bucket_calls_api_method_with_args(self, run):
        bucket = self.create_sarge().new_bucket()
        imp('sarge.core').main([str(self.tmp), 'run', bucket.id_, 'a'])
        self.assertEqual(run.mock_calls, [call('a')])

    @patch('sarge.core.Sarge.list_buckets')
    def test_destroy_bucket_calls_api_method(self, list_buckets):
        data = {'some': ['json', 'data']}
        list_buckets.return_value = data
        with patch('sys.stdout', StringIO()) as stdout:
            config = json.dumps({'hello': "world"})
            imp('sarge.core').main([str(self.tmp), 'list'])
        self.assertEqual(list_buckets.mock_calls, [call()])
        self.assertEqual(json.loads(stdout.getvalue()), data)

    def test_init_creates_configuration_and_bin_scripts(self):
        other_tmp = path(tempfile.mkdtemp())
        self.addCleanup(other_tmp.rmtree)

        core = imp('sarge.core')
        core.main([str(other_tmp), 'init'])
        expected = ['bin', 'etc', 'var']
        self.assertItemsEqual([f.name for f in other_tmp.listdir()], expected)
        self.assertItemsEqual([f.name for f in (other_tmp / 'bin').listdir()],
                              ['sarge', 'supervisord', 'supervisorctl'])
        sarge_yaml_path = other_tmp / 'etc' / 'sarge.yaml'
        self.assertTrue(sarge_yaml_path.isfile())
        self.assertIsNotNone(json.loads(sarge_yaml_path.text()))
