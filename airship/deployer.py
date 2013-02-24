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


@bucket_setup.connect
def set_up_virtualenv_and_requirements(bucket, **extra):
    airship = bucket.airship
    requirements_file = bucket.folder / 'requirements.txt'
    if requirements_file.isfile():
        index_dir = airship.config['python_dist']
        venv = bucket.folder / '_virtualenv'
        pip = venv / 'bin' / 'pip'
        virtualenv_py = airship.home_path / 'dist' / 'virtualenv.py'
        python = airship.config.get('python_interpreter', 'python')

        try:
            subprocess.check_call([python, virtualenv_py, venv,
                                   '--distribute', '--never-download',
                                   '--extra-search-dir=' + index_dir])
        except subprocess.CalledProcessError:
            raise DeployError(bucket, "Failed to create a virtualenv.")

        try:
            subprocess.check_call([pip, 'install', 'wheel', '--no-index',
                                   '--find-links=file://' + index_dir])
        except subprocess.CalledProcessError:
            raise DeployError(bucket, "Failed to install wheel.")

        try:
            subprocess.check_call([pip, 'install', '-r', requirements_file,
                                   '--use-wheel', '--no-index',
                                   '--find-links=file://' + index_dir])
        except subprocess.CalledProcessError:
            raise DeployError(bucket, "Failed to install requirements.")


@bucket_setup.connect
def set_up_script(bucket):
    procname = 'web'
    procs = get_procs(bucket)
    server_script = bucket.folder / '_run_process'
    server_script.write_text('exec %s\n' % procs[procname])
    server_script.chmod(0755)


def remove_old_buckets(bucket):
    airship = bucket.airship
    for bucket_info in airship.list_buckets()['buckets']:
        if bucket_info['id'] == bucket.id_:
            continue
        airship.get_bucket(bucket_info['id']).destroy()


def deploy(airship, tarfile):
    bucket = airship.new_bucket()
    subprocess.check_call(['tar', 'xf', tarfile, '-C', bucket.folder])
    bucket_setup.send(bucket)
    remove_old_buckets(bucket)
    try:
        bucket.start()
    except SupervisorError:
        raise DeployError(bucket, "Failed to start bucket.")
