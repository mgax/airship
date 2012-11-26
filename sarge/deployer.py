import subprocess
import blinker


bucket_setup = blinker.Signal()


def get_procs(bucket):
    with (bucket.folder / 'Procfile').open('rb') as f:
        return dict((k.strip(), v.strip()) for k, v in
                    (l.split(':', 1) for l in f))


@bucket_setup.connect
def set_up_virtualenv_and_requirements(bucket, **extra):
    sarge = bucket.sarge
    requirements_file = bucket.folder / 'requirements.txt'
    if requirements_file.isfile():
        index_dir = sarge.config['wheel_index_dir']
        venv = bucket.folder / '_virtualenv'
        pip = venv / 'bin' / 'pip'
        virtualenv_py = sarge.home_path / 'dist' / 'virtualenv.py'
        python = sarge.config.get('virtualenv_python_bin', 'python')

        subprocess.check_call([python, virtualenv_py, venv,
                               '--distribute', '--never-download',
                               '--extra-search-dir=' + index_dir])
        subprocess.check_call([pip, 'install', 'wheel', '--no-index',
                               '--find-links=file://' + index_dir])
        subprocess.check_call([pip, 'install', '-r', requirements_file,
                               '--use-wheel', '--no-index',
                               '--find-links=file://' + index_dir])


@bucket_setup.connect
def set_up_script(bucket):
    procname = bucket.meta['APPLICATION_NAME']
    procs = get_procs(bucket)
    server_script = bucket.folder / '_run_process'
    server_script.write_text('exec %s\n' % procs[procname])
    server_script.chmod(0755)


def remove_old_buckets(bucket):
    sarge = bucket.sarge
    procname = bucket.meta['APPLICATION_NAME']
    for bucket_info in sarge.list_buckets()['buckets']:
        if bucket_info['meta']['APPLICATION_NAME'] == procname:
            if bucket_info['id'] == bucket.id_:
                continue
            sarge.get_bucket(bucket_info['id']).destroy()


def deploy(sarge, tarfile, procname):
    bucket = sarge.new_bucket({'application_name': procname})
    subprocess.check_call(['tar', 'xf', tarfile, '-C', bucket.folder])
    bucket_setup.send(bucket)
    remove_old_buckets(bucket)
    bucket.start()
