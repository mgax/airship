from datetime import datetime
import json
from mock import Mock, patch, call
from common import AirshipTestCase


class ProgramsRecorder(object):

    def __init__(self):
        self.programs = []

    def __call__(self, bucket_id, programs):
        self.programs.extend([{'name': name, 'command': p['command']}
                              for name, p in programs])


class BucketTest(AirshipTestCase):

    def test_new_bucket_creates_bucket_folder(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket()
        self.assertTrue(bucket.folder.isdir())

    def test_get_bucket_returns_bucket_with_correct_folder(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket()
        same_bucket = sarge.get_bucket(bucket.id_)
        self.assertEqual(bucket.folder, same_bucket.folder)

    def test_get_bucket_with_app_name_returns_bucket(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket({'application_name': 'jack'})
        same_bucket = sarge.get_bucket('jack')
        self.assertEqual(bucket.folder, same_bucket.folder)

    def test_get_bucket_with_invalid_name_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.create_sarge().get_bucket('nonesuch')

    def test_start_bucket_configures_daemon_to_running(self):
        sarge = self.create_sarge()
        sarge.daemons = Mock()
        bucket = sarge.new_bucket()
        bucket.start()
        self.assertEqual(sarge.daemons.configure_bucket_running.mock_calls,
                         [call(bucket)])

    def test_trigger_bucket_calls_daemon_start(self):
        sarge = self.create_sarge()
        sarge.daemons = Mock()
        bucket = sarge.new_bucket()
        bucket.trigger()
        self.assertEqual(sarge.daemons.trigger_bucket.mock_calls,
                         [call(bucket)])

    def test_service_is_configured_at_bucket_creation(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket({'services': {
            'something': {'foo': 'bar'},
        }})

        services = bucket.config['require-services']
        self.assertEqual(services['something'], {'foo': 'bar'})

    def test_two_buckets_have_different_paths_and_ids(self):
        sarge = self.create_sarge()
        bucket_1 = sarge.new_bucket()
        bucket_2 = sarge.new_bucket()
        self.assertNotEqual(bucket_1.folder, bucket_2.folder)
        self.assertNotEqual(bucket_1.id_, bucket_2.id_)

    def test_unlucky_bucket_id_generator_gives_up(self):
        sarge = self.create_sarge()
        with patch('airship.core.random') as random:
            random.choice.return_value = 'z'
            sarge.new_bucket()
            with self.assertRaises(RuntimeError):
                sarge.new_bucket()

    def test_bucket_metadata_contains_creation_time(self):
        sarge = self.create_sarge()
        t0 = datetime.utcnow().isoformat()
        bucket = sarge.new_bucket()
        t1 = datetime.utcnow().isoformat()
        creation = bucket.meta['CREATION_TIME']
        self.assertTrue(t0 <= creation <= t1)

    def test_bucket_metadata_contains_app_name(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket({'application_name': 'testy'})
        self.assertEqual(bucket.meta['APPLICATION_NAME'], 'testy')

    def test_bucket_id_starts_with_app_name(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket({'application_name': 'testy'})
        self.assertTrue(bucket.id_.startswith('testy-'))


class BucketPortAllocationTest(AirshipTestCase):

    def test_new_bucket_allocates_port(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket()
        self.assertTrue(1024 <= bucket.port < 65536)

    def test_new_buckets_have_different_ports(self):
        sarge = self.create_sarge()
        bucket1 = sarge.new_bucket()
        bucket2 = sarge.new_bucket()
        self.assertNotEqual(bucket1.port, bucket2.port)

    def test_destroyed_buckets_free_their_ports(self):
        sarge = self.create_sarge()
        bucket1 = sarge.new_bucket()
        bucket2 = sarge.new_bucket()
        allocated = lambda: set(sarge._open_ports_db()) - set(['next'])
        self.assertItemsEqual(allocated(), [bucket1.port, bucket2.port])
        bucket1.destroy()
        self.assertItemsEqual(allocated(), [bucket2.port])

    def test_ports_allocated_sequentially_even_after_bucket_destroyed(self):
        sarge = self.create_sarge()
        bucket1 = sarge.new_bucket()
        bucket2 = sarge.new_bucket()
        bucket1.destroy()
        bucket3 = sarge.new_bucket()
        self.assertEqual(bucket3.port, bucket2.port + 1)

    def test_port_allocation_wraps_when_it_reaches_interval_end(self):
        sarge = self.create_sarge({'port_range': [5000, 5009]})
        i0_i1 = [sarge.new_bucket() for c in range(2)]
        i2_i7 = [sarge.new_bucket() for c in range(6)]
        for bucket in i0_i1:
            bucket.destroy()
        i8_i9 = [sarge.new_bucket() for c in range(2)]
        for bucket in i8_i9:
            bucket.destroy()
        i10_i13 = [sarge.new_bucket() for c in range(4)]
        self.assertEqual([i.port for i in i10_i13],
                         [5000, 5001, 5008, 5009])
        self.assertRaises(RuntimeError, sarge.new_bucket)  # no more ports

    def test_port_allocation_shifts_in_range_if_next_port_is_too_low(self):
        sarge1 = self.create_sarge({'port_range': [5000, 5009]})
        b1 = sarge1.new_bucket()
        self.assertEqual(b1.port, 5000)
        sarge2 = self.create_sarge({'port_range': [6000, 6009]})
        b2 = sarge2.new_bucket()
        self.assertEqual(b2.port, 6000)

    def test_port_allocation_shifts_in_range_if_next_port_is_too_high(self):
        sarge1 = self.create_sarge({'port_range': [6000, 6009]})
        b1 = sarge1.new_bucket()
        self.assertEqual(b1.port, 6000)
        sarge2 = self.create_sarge({'port_range': [5000, 5009]})
        b2 = sarge2.new_bucket()
        self.assertEqual(b2.port, 5000)


class BucketListingTest(AirshipTestCase):

    def test_listing_with_no_buckets_returns_empty_list(self):
        sarge = self.create_sarge()
        report = sarge.list_buckets()
        self.assertEqual(report['buckets'], [])

    def test_listing_with_two_buckets_contains_their_ids(self):
        sarge = self.create_sarge()
        bucket_1 = sarge.new_bucket()
        bucket_2 = sarge.new_bucket()
        report = sarge.list_buckets()
        self.assertItemsEqual([i['id'] for i in report['buckets']],
                              [bucket_1.id_, bucket_2.id_])

    def test_listing_contains_metadata(self):
        sarge = self.create_sarge()
        sarge.new_bucket({'application_name': 'testy'})
        report = sarge.list_buckets()
        [bucket_data] = report['buckets']
        self.assertEqual(bucket_data['meta']['APPLICATION_NAME'], 'testy')

    def test_listing_contains_port(self):
        sarge = self.create_sarge()
        bucket = sarge.new_bucket()
        report = sarge.list_buckets()
        [bucket_data] = report['buckets']
        self.assertEqual(bucket_data['port'], bucket.port)


class BucketRunTest(AirshipTestCase):

    def setUp(self):
        self.os = self.patch('airship.core.os')
        self.os.environ = {}
        self.get_environ = lambda: self.os.execve.mock_calls[-1][1][2]

    def test_run_prepares_environ_from_etc_app_config(self):
        env = {'SOME_CONFIG_VALUE': "hello there!"}
        self.create_sarge({'env': env}).new_bucket().run(None)
        environ = self.get_environ()
        self.assertEqual(environ['SOME_CONFIG_VALUE'], "hello there!")

    def test_run_inserts_port_in_environ(self):
        bucket = self.create_sarge().new_bucket()
        bucket.run(None)
        environ = self.get_environ()
        self.assertEqual(environ['PORT'], str(bucket.port))
