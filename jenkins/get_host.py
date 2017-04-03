#!/bin/env python
"""
This script queries vagrant ssh-config to get the correct ssh hostname and port.
Output is in Ansible inventory format. This script is intended to be used by
jenkins. Jenkins runs vagrant with docker vms. Docker vms do not (easily)
support adding ip addresses. Vagrant handles this port forwarding automatically,
so better use that.

Example:
  [development]
  172.17.0.11:22
"""
import subprocess
import re
import json
import sys

res = subprocess.Popen(["vagrant", "ssh-config"], stdout=subprocess.PIPE)
re_host = re.compile("\s+HostName\s(.*)")
re_port = re.compile("\s+Port\s(\d+)")
hostname = None
port = None


for l in res.stdout:
    m_host = re_host.match(l)
    m_port = re_port.match(l)
    if m_host:
        hostname = m_host.group(1)
    if m_port:
        port = m_port.group(1)

if sys.argv:
    if sys.argv[1] == '--list':
        print json.dumps({
            "jenkins": {
                "hosts": ["{0}".format(hostname)]
            },
            "_meta": {
                "hostvars": {
                    "jenkins": {
                        "ansible_ssh_host": hostname,
                        "ansible_ssh_port": port,
                        "server_name": hostname
                    }
                }
            }
        }, indent=4)

    if sys.argv[1] == '--host':
        print "{}"
