import subprocess


def get_procs(bucket):
    with (bucket.folder / 'Procfile').open('rb') as f:
        return dict((k.strip(), v.strip()) for k, v in
                    (l.split(':', 1) for l in f))


def deploy(sarge, tarfile, procname):
    bucket = sarge.new_bucket({'application_name': procname})

    subprocess.check_call(['tar', 'xf', tarfile, '-C', bucket.folder])
    procs = get_procs(bucket)

    server_script = bucket.folder / '_run_process'
    server_script.write_text('exec %s\n' % procs[procname])
    server_script.chmod(0755)

    for bucket_info in sarge.list_buckets()['buckets']:
        if bucket_info['meta']['APPLICATION_NAME'] == procname:
            if bucket_info['id'] == bucket.id_:
                continue
            sarge.get_bucket(bucket_info['id']).destroy()

    bucket.start()
