import subprocess
import blinker
from .daemons import SupervisorError


bucket_setup = blinker.Signal()


class DeployError(Exception):
    """ Something went wrong during deployment. """

    def __init__(self, bucket, message):
        super(DeployError, self).__init__(message)
        self.bucket = bucket


def get_procs(bucket):
    with (bucket.folder / 'Procfile').open('rb') as f:
        return dict((k.strip(), v.strip()) for k, v in
                    (l.split(':', 1) for l in f))


def remove_old_buckets(bucket):
    airship = bucket.airship
    for bucket_info in airship.list_buckets()['buckets']:
        if bucket_info['id'] == bucket.id_:
            continue
        airship.get_bucket(bucket_info['id']).destroy()


def deploy(airship, tarfile):
    bucket = airship.new_bucket()
    subprocess.check_call(['tar', 'xf', tarfile, '-C', bucket.folder])
    bucket._read_procfile()
    bucket_setup.send(bucket)
    remove_old_buckets(bucket)
    try:
        bucket.start()
    except SupervisorError:
        raise DeployError(bucket, "Failed to start bucket.")
