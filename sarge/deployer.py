import subprocess


def get_procs(instance):
    with (instance.folder / 'Procfile').open('rb') as f:
        return dict((k.strip(), v.strip()) for k, v in
                    (l.split(':', 1) for l in f))


def deploy(sarge, tarfile, procname):
    instance = sarge.new_instance({'application_name': procname})

    subprocess.check_call(['tar', 'xf', tarfile, '-C', instance.folder])
    procs = get_procs(instance)

    server_script = instance.folder / 'server'
    server_script.write_text('exec %s\n' % procs[procname])
    server_script.chmod(0755)

    for instance_info in sarge.list_instances()['instances']:
        if instance_info['meta']['APPLICATION_NAME'] == procname:
            if instance_info['id'] == instance.id_:
                continue
            sarge.get_instance(instance_info['id']).destroy()

    instance.start()
