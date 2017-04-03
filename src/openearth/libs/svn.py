import subprocess
from urlparse import urlparse, urlunparse
from collections import defaultdict

try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET


class SvnException(Exception):
    pass


class SvnRepoDoesNotExist(SvnException):
    pass


def xml_to_dict(t):
    # Source: http://stackoverflow.com/a/10077069
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(xml_to_dict, children):
            for k, v in dc.iteritems():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.iteritems()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.iteritems())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def kwargs_to_args(**kwargs):
    args = []
    for k, v in kwargs.iteritems():
        k = k.replace('_', '-')
        if v:
            args.append('--%s=%s' % (k, v))
        else:
            args.append('--%s' % k)

    return ' '.join(args)


def command(command, url, **kwargs):
    args = kwargs_to_args(non_interactive=None, trust_server_cert=None,
                          **kwargs)

    full_command = ' '.join(('svn', command, urlunparse(urlparse(url)), args))
    p = subprocess.Popen(
        full_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)

    return p.communicate()


def list_(url, username, password):
    output, err = command('list', url, username=username, password=password)
    return output.splitlines(), err


def revisions(url, username, password, limit=10, revision=None):
    kwargs = dict()
    if revision:
        kwargs['revision'] = revision

    xml, err = command('log', url, username=username, password=password,
                       limit=limit, xml=None, **kwargs)

    try:
        revisions = xml_to_dict(ET.XML(xml))['log']['logentry']

        if isinstance(revisions, dict):
            revisions = [revisions]

        return revisions
    except ET.ParseError:
        raise SvnRepoDoesNotExist(url, revision)

