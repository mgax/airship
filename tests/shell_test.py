import tempfile
from StringIO import StringIO
import json
from path import path
from mock import Mock, patch, call
from common import AirshipTestCase, imp


class ShellTest(AirshipTestCase):

    def setUp(self):
        (self.tmp / 'etc' / 'airship.yaml').write_text('{}')

    @patch('airship.core.Bucket.destroy')
    def test_destroy_bucket_calls_api_method(self, destroy):
        bucket = self.create_airship().new_bucket()
        imp('airship.core').main([str(self.tmp), 'destroy', bucket.id_])
        self.assertEqual(destroy.mock_calls, [call()])

    @patch('airship.core.Bucket.run')
    def test_run_bucket_calls_api_method_with_args(self, run):
        bucket = self.create_airship().new_bucket()
        imp('airship.core').main([str(self.tmp), 'run', bucket.id_, 'a'])
        self.assertEqual(run.mock_calls, [call('a')])

    @patch('airship.core.Airship.list_buckets')
    def test_destroy_bucket_calls_api_method(self, list_buckets):
        data = {'some': ['json', 'data']}
        list_buckets.return_value = data
        with patch('sys.stdout', StringIO()) as stdout:
            config = json.dumps({'hello': "world"})
            imp('airship.core').main([str(self.tmp), 'list'])
        self.assertEqual(list_buckets.mock_calls, [call()])
        self.assertEqual(json.loads(stdout.getvalue()), data)

    def test_init_creates_configuration_and_bin_scripts(self):
        other_tmp = path(tempfile.mkdtemp())
        self.addCleanup(other_tmp.rmtree)

        core = imp('airship.core')
        core.main([str(other_tmp), 'init'])
        expected = ['bin', 'etc', 'var']
        self.assertItemsEqual([f.name for f in other_tmp.listdir()], expected)
        self.assertItemsEqual([f.name for f in (other_tmp / 'bin').listdir()],
                              ['airship', 'supervisord', 'supervisorctl'])
        airship_yaml_path = other_tmp / 'etc' / 'airship.yaml'
        self.assertTrue(airship_yaml_path.isfile())
