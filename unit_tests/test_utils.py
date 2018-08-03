# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import os
import logging
import unittest

import yaml
import six

from contextlib import contextmanager
from mock import patch, MagicMock


def load_config():
    '''
    Walk backwords from __file__ looking for config.yaml, load and return the
    'options' section'
    '''
    config = None
    f = __file__
    while config is None:
        d = os.path.dirname(f)
        if os.path.isfile(os.path.join(d, 'config.yaml')):
            config = os.path.join(d, 'config.yaml')
            break
        f = d

    if not config:
        logging.error('Could not find config.yaml in any parent directory '
                      'of %s. ' % f)
        raise Exception

    return yaml.safe_load(open(config).read())['options']


def get_default_config():
    '''
    Load default charm config from config.yaml return as a dict.
    If no default is set in config.yaml, its value is None.
    '''
    default_config = {}
    config = load_config()
    for k, v in six.iteritems(config):
        if 'default' in v:
            default_config[k] = v['default']
        else:
            default_config[k] = None
    return default_config


class CharmTestCase(unittest.TestCase):

    def setUp(self, obj, patches):
        super(CharmTestCase, self).setUp()
        self.originals = {}
        self.patches = patches
        self.obj = obj
        self.test_config = TestConfig()
        self.test_relation = TestRelation()
        self.patch_all()

    def patch(self, method):
        self.originals[method] = getattr(self.obj, method)
        _m = patch.object(self.obj, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def patch_all(self):
        for method in self.patches:
            setattr(self, method, self.patch(method))


class TestConfig(object):

    def __init__(self):
        self.config = get_default_config()

    def get(self, attr=None):
        if not attr:
            return self.get_all()
        try:
            return self.config[attr]
        except KeyError:
            return None

    def get_all(self):
        return self.config

    def set(self, attr, value):
        if attr not in self.config:
            raise KeyError
        self.config[attr] = value


class TestRelation(object):

    def __init__(self, relation_data={}):
        self.relation_data = relation_data

    def set(self, relation_data):
        self.relation_data = relation_data

    def get(self, attr=None, unit=None, rid=None):
        if attr is None:
            return self.relation_data
        elif attr in self.relation_data:
            return self.relation_data[attr]
        return None


@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    open_name = get_open_name()
    if six.PY3:
        open_func = open_name
        file_func = io.FileIO
    else:
        open_func = open
        file_func = file

    mock_open = MagicMock(spec=open_func)
    mock_file = MagicMock(spec=file_func)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch(open_name, stub_open):
        yield mock_open, mock_file


def get_open_name():
    '''Returns the name of the open() function'''
    if six.PY3:
        return 'builtins.open'
    else:
        return '__builtin__.open'
