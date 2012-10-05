import subprocess


def get_procs(instance):
    with (instance.folder / 'Procfile').open('rb') as f:
        return dict((k.strip(), v.strip()) for k, v in
                    (l.split(':', 1) for l in f))


def deploy(sarge, tarfile, procname):
    for instance_info in sarge.list_instances()['instances']:
        if instance_info['meta']['APPLICATION_NAME'] == procname:
            sarge.get_instance(instance_info['id']).destroy()

    instance = sarge.new_instance({'application_name': procname})
    instance_id = instance.id_

    subprocess.check_call(['tar', 'xf', tarfile, '-C', instance.folder])
    procs = get_procs(instance)

    server_script = instance.folder / 'server'
    server_script.write_text('exec %s\n' % procs[procname])
    server_script.chmod(0755)

    instance.start()
