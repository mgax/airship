import subprocess


def get_procs(bucket):
    with (bucket.folder / 'Procfile').open('rb') as f:
        return dict((k.strip(), v.strip()) for k, v in
                    (l.split(':', 1) for l in f))


def deploy(sarge, tarfile, procname):
    bucket = sarge.new_bucket({'application_name': procname})

    subprocess.check_call(['tar', 'xf', tarfile, '-C', bucket.folder])
    procs = get_procs(bucket)

    requirements_file = bucket.folder / 'requirements.txt'
    if requirements_file.isfile():
        index_dir = sarge.config['wheel_index_dir']
        venv = bucket.folder / '_virtualenv'
        pip = venv / 'bin' / 'pip'
        python = sarge.config.get('virtualenv_python_bin', 'python')

        subprocess.check_call(['virtualenv', venv, '--python=' + python,
                               '--distribute', '--never-download',
                               '--extra-search-dir=' + index_dir])
        subprocess.check_call([pip, 'install', 'wheel', '--no-index',
                               '--find-links=file://' + index_dir])
        subprocess.check_call([pip, 'install', '-r', requirements_file,
                               '--use-wheel', '--no-index',
                               '--find-links=file://' + index_dir])

    server_script = bucket.folder / '_run_process'
    server_script.write_text('exec %s\n' % procs[procname])
    server_script.chmod(0755)

    for bucket_info in sarge.list_buckets()['buckets']:
        if bucket_info['meta']['APPLICATION_NAME'] == procname:
            if bucket_info['id'] == bucket.id_:
                continue
            sarge.get_bucket(bucket_info['id']).destroy()

    bucket.start()
