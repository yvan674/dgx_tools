"""Container Inspect

Inspects docker containers and which user started which docker container and
the resource utilization of each container.

Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    January 16, 2020
"""
from subprocess import check_output
import json
try:
    import GPUtil
except ImportError:
    print("Warning: GPUtil not found. GPU information will not be displayed."
          "\n")
    GPUtil = None


def get_docker_ids():
    """Gets docker container IDs

    :returns: List of container IDs as strings
    :rtype: list

    """
    results = check_output(["docker", "ps", "-q"]).decode('ascii')
    return str(results).split('\n')[:-1]


def get_user(mounts):
    """Gets user ID from the Mount source

    :param list mounts: The 'Mounts' value from docker inspect.
    :return: User ID.
    :rtype: str
    """
    mount = []
    for i, x in enumerate(mounts):
        mount.append(x['Source'].split('/'))
        if not mount[i][0]:
            del mount[i][0]

    # We assume that the 2nd value of the mount is the user. We check by making
    # sure that the first and the second values are cluster and [home | data]
    # We also assume the last mount is the correct one.
    for m in mount:
        try:
            if m[0] == 'cluster' and (m[1] == 'data' or m[1] == 'home'):
                return m[2]
            else:
                continue
        except IndexError:
            continue

    # If we've gone through everything and still haven't found the user:
    return "Unknown"

def get_gpus(env, gpu_list):
    """Gets GPU IDs given the GPU UUIDs.

    :param list env: Container environment variables.
    :param list gpu_list: List of GPUs from GPUtil.
    :return: List of GPU IDs.
    :rtype: list
    """
    used_ids = []
    uuids = []

    for var in env:
        if 'NVIDIA_VISIBLE_DEVICES' in var:
            var = var.split('=')[1].split(',')
            for x in var:
                uuids.append(x)

    if not uuids[0]:
        return '-', '0'

    for uuid in uuids:
        for gpu in gpu_list:
            if gpu.uuid == uuid:
                used_ids.append(str(gpu.id))

    return ', '.join(used_ids), str(len(used_ids))


def count_cpus(cpusets):
    """Counts CPUs used."""
    cpus_used = 0
    cpu_sets = cpusets.split(',')
    for cpu_set in cpu_sets:
        s = cpu_set.split('-')
        if len(s) > 1:
            cpus_used += int(s[1]) - int(s[0])
            cpus_used += 1
        else:
            cpus_used += 1
    return str(cpus_used)


def inspect_containers(container_ids, gpu_list):
    """Inspects containers and returns relevant information.

    Each given container ID is inspected and relevant information is collected.
    Relevant information collected is the user that created it, its docker
    image, CPUs used, and GPUs used.

    :param list container_ids: List of container IDs.
    :param list gpu_list: List of GPUs from GPUtil
    :return: A list of dictionaries containing ['ID', 'Name', 'User', 'Image,
        'CPUs Used', 'CPU Count', 'GPUs Used']]
    :rtype: list
    """
    out_list = []
    for id in container_ids:
        info = {}
        info['ID'] = id

        inspection = check_output(["docker", "inspect", id]).decode('ascii')
        inspection = json.loads(inspection)[0]

        info['Name'] = inspection['Name'][1:]
        info['CpusUsed'] = inspection['HostConfig']['CpusetCpus']
        info['CpuCount'] = count_cpus(info['CpusUsed'])

        # Get user name, assuming that it will be the container will be mounted
        # to either
        info['User'] = get_user(inspection['Mounts'])

        if GPUtil:
            info['GpusUsed'], info['GpuCount'] = get_gpus(
                inspection['Config']['Env'], gpu_list
            )

        info['Image'] = inspection['Config']['Image'].split(':')[0]

        out_list.append(info)
    return out_list


def output(info):
    """Outputs info nicely in a table."""
    names = [4]
    cpus_used = [9]
    users = [4]
    gpus_used = [9]
    images = [5]
    for container in info:
        names.append(len(container['Name']))
        cpus_used.append(len(container['CpusUsed']))
        users.append(len(container['User']))
        if GPUtil:
            gpus_used.append(len(container['GpusUsed']))
        images.append(len(container['Image']))

    string_form = "{:<12} {:<"
    string_form += str(max(names) + 1)
    string_form += "} {:<"
    string_form += str(max(users) + 1)
    string_form += "} {:<"
    string_form += str(max(images) + 1)
    string_form += "} {:>"
    string_form += str(max(cpus_used))
    string_form += "} {:>9"
    if GPUtil:
        string_form += "} {:>"
        string_form += str(max(gpus_used) + 1)
        string_form += "} {:>9"
    string_form += "}"

    headers = ['ID', "Name", "User", "Image", "CPUs Used", "CPU Count"]

    if GPUtil:
        headers += ["GPUs Used", "GPU Count"]

    print("\033[47;30m" + string_form.format(*headers) + "\033[49;39m")

    for container in info:
        data = [
            container['ID'],
            container['Name'],
            container['User'],
            container['Image'],
            container['CpusUsed'],
            container['CpuCount'],
        ]

        if GPUtil:
            data += [container['GpusUsed'], container['GpuCount']]

        print("" + string_form.format(*data))
    print('')


if __name__ == '__main__':
    container_ids = get_docker_ids()
    gpu_list = GPUtil.getGPUs() if GPUtil else []
    info = inspect_containers(container_ids, gpu_list)
    output(info)
