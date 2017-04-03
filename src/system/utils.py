import os
import re
import time
import subprocess

MOUNT_TIMEOUT = 1  # Mount output timeout in seconds
MOUNT_RE = re.compile('^(?P<disk>.+?) on (?P<name>[^ ]+)', re.MULTILINE)
MOUNT_EXCLUDES_RE = re.compile('^/(dev|proc|sys|boot)($|/.*)')


def get_mounts():
    process = subprocess.Popen('mount', stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE)

    return_code = None
    start_time = time.time()
    while return_code is None and time.time() - start_time < MOUNT_TIMEOUT:
        time.sleep(0.01)
        return_code = process.poll()

    if return_code is None:
        raise RuntimeError('Mount command timed out, please report to '
                           'the sysadmin immediately!')
    elif return_code == 0:
        mount_output = process.stdout.read()
        for match in MOUNT_RE.finditer(mount_output):
            if not MOUNT_EXCLUDES_RE.match(match.group('name')):
                yield match.groupdict()

    else:
        raise RuntimeError('Mount command returned signal %d, output: %s %s' % (
            return_code, process.stdout.read(), process.stderr.read()))


def get_disk_usage(name):
    statvfs = os.statvfs(name)

    return dict(
        name=name,
        size=statvfs.f_frsize * statvfs.f_blocks,
        free=statvfs.f_frsize * statvfs.f_bavail,
        used=statvfs.f_frsize * (statvfs.f_blocks - statvfs.f_bfree),
        reserved=statvfs.f_frsize * (statvfs.f_bfree - statvfs.f_bavail),
    )


def get_disk_usages():
    return [get_disk_usage(mount['name']) for mount in get_mounts()]


if __name__ == '__main__':
    get_disk_usages()
