import re
import os
import ConfigParser
from collections import OrderedDict
from os.path import dirname, join, normpath, abspath


class MultiOrderedDict(OrderedDict):
    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        if isinstance(value, list) and key in self:
            self[key].extend(value)
        else:
            super(OrderedDict, self).__setitem__(key, value)


def read_env(path=None):

    if path is None:
        path = normpath(join(dirname(dirname(dirname(dirname(abspath(__file__))))), 'etc/env.ini'))

    try:
        config = ConfigParser.ConfigParser(dict_type=MultiOrderedDict)
        config.read(path)
        config = config.get('uwsgi', 'env')
    except IOError:
        config = []

    for env_var in config:
        m1 = re.match(r'\A([A-Za-z_0-9]+)=(.*)\Z', env_var)
        if m1:
            key, val = m1.group(1), m1.group(2)
            m2 = re.match(r"\A'(.*)'\Z", val)
            if m2:
                val = m2.group(1)
            m3 = re.match(r'\A"(.*)"\Z', val)
            if m3:
                val = re.sub(r'\\(.)', r'\1', m3.group(1))
            os.environ.setdefault(key, val)
