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
        airship = self.create_airship()
        bucket = airship.new_bucket()
        self.assertTrue(bucket.folder.isdir())

    def test_get_bucket_returns_bucket_with_correct_folder(self):
        airship = self.create_airship()
        bucket = airship.new_bucket()
        same_bucket = airship.get_bucket(bucket.id_)
        self.assertEqual(bucket.folder, same_bucket.folder)

    def test_get_bucket_with_no_args_returns_bucket(self):
        airship = self.create_airship()
        bucket = airship.new_bucket()
        same_bucket = airship.get_bucket()
        self.assertEqual(bucket.folder, same_bucket.folder)

    def test_get_bucket_with_invalid_name_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.create_airship().get_bucket('nonesuch')

    def test_start_bucket_configures_daemon_to_running(self):
        airship = self.create_airship()
        airship.daemons = Mock()
        bucket = airship.new_bucket()
        bucket.start()
        self.assertEqual(airship.daemons.configure_bucket_running.mock_calls,
                         [call(bucket)])

    def test_trigger_bucket_calls_daemon_start(self):
        airship = self.create_airship()
        airship.daemons = Mock()
        bucket = airship.new_bucket()
        bucket.trigger()
        self.assertEqual(airship.daemons.trigger_bucket.mock_calls,
                         [call(bucket)])

    def test_two_buckets_have_different_paths_and_ids(self):
        airship = self.create_airship()
        bucket_1 = airship.new_bucket()
        bucket_2 = airship.new_bucket()
        self.assertNotEqual(bucket_1.folder, bucket_2.folder)
        self.assertNotEqual(bucket_1.id_, bucket_2.id_)

    def test_unlucky_bucket_id_generator_gives_up(self):
        airship = self.create_airship()
        with patch('airship.core.random') as random:
            random.choice.return_value = 'z'
            airship.new_bucket()
            with self.assertRaises(RuntimeError):
                airship.new_bucket()

    def test_bucket_metadata_contains_creation_time(self):
        airship = self.create_airship()
        t0 = datetime.utcnow().isoformat()
        bucket = airship.new_bucket()
        t1 = datetime.utcnow().isoformat()
        creation = bucket.meta['CREATION_TIME']
        self.assertTrue(t0 <= creation <= t1)


class BucketListingTest(AirshipTestCase):

    def test_listing_with_no_buckets_returns_empty_list(self):
        airship = self.create_airship()
        report = airship.list_buckets()
        self.assertEqual(report['buckets'], [])

    def test_listing_with_two_buckets_contains_their_ids(self):
        airship = self.create_airship()
        bucket_1 = airship.new_bucket()
        bucket_2 = airship.new_bucket()
        report = airship.list_buckets()
        self.assertItemsEqual([i['id'] for i in report['buckets']],
                              [bucket_1.id_, bucket_2.id_])
