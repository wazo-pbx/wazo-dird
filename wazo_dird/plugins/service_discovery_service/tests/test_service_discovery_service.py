# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import tempfile
import unittest

from hamcrest import assert_that, equal_to, not_
from mock import sentinel as s

from ..plugin import (
    ProfileConfigUpdater,
    SourceConfigGenerator,
    SourceConfigManager,
)


TEMPLATE = '''\
type: wazo
name: wazo-{{ uuid }}
searched_columns:
  - firstname
  - lastname
first_matched_columns:
  - exten
auth:
  host: {{ hostname }}
  port: 9497
confd:
  host: {{ hostname }}
  port: {{ port }}
  version: "1.1"
format_columns:
    number: "{exten}"
    reverse: "{firstname} {lastname}"
    voicemail: "{voicemail_number}"
'''

CONFIG = {
    'services': {
        'lookup': {
            'foobar': {'sources': {'source_1': True, 'source_2': True}},
            'default': {'sources': {'source_2': True}},
        },
        'reverse': {
            'foobar': {'sources': {'source_1': True, 'source_2': True}},
            'default': {'sources': {'source_2': True}},
        },
        'favorites': {
            'foobar': {'sources': {'source_2': True}},
            'default': {'sources': {'source_2': True}},
        },
        'service_discovery': {
            'template_path': None,
            'services': {
                'xivo-confd': {
                    'template': None,
                    'lookup': {
                        'foobar': True,
                        'default': True,
                        '__switchboard': False,
                    },
                    'reverse': {
                        'foobar': True,
                        'default': False,
                        '__switchboard': True,
                    },
                    'favorites': {
                        'foobar': True,
                        'default': True,
                        '__switboard': False,
                    },
                },
            },
            'hosts': {
                'ff791b0e-3d28-4b4d-bb90-2724c0a248cb': {
                    'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        },
    },
}


class TestServiceDiscoveryServicePlugin(unittest.TestCase):
    pass


class TestServiceDiscoveryService(unittest.TestCase):

    def test_that_the_service_looks_for_remote_servers_when_starting(self):
        pass


def new_template_file(content):
    f = tempfile.NamedTemporaryFile(delete=False)
    with open(f.name, 'w') as f:
        f.write(content)
    dir_, name = os.path.split(f.name)
    return f, dir_, name


class TestSourceConfigManager(unittest.TestCase):

    def setUp(self):
        self.source_config = {
            "personal": {
                "name": "personal",
                "type": "personal",
            },
            "xivodir": {
                "name": "xivodir",
                "type": "phonebook",
            },
            None: {
                "name": None,
                "type": "invalid",
            },
        }

    def test_source_exists(self):
        manager = SourceConfigManager(self.source_config)

        assert_that(manager.source_exists('personal'))
        assert_that(not_(manager.source_exists('foobar')))
        assert_that(not_(manager.source_exists(None)))

    def test_add_source(self):
        manager = SourceConfigManager(self.source_config)

        foobar_config = {'name': 'foobar',
                         'type': 'phonebook'}

        manager.add_source(foobar_config)

        assert_that(self.source_config['foobar'], equal_to(foobar_config))


class TestSourceConfigGenerator(unittest.TestCase):

    def setUp(self):
        (self.template_file,
         self.template_dir,
         self.template_filename) = new_template_file(TEMPLATE)

    def tearDown(self):
        try:
            os.unlink(self.template_file.name)
        except OSError:
            return

    def test_generate_with_an_unknown_service(self):
        service_discovery_config = {
            'template_path': None,
            'services': {},
            'hosts': {
                'ff791b0e-3d28-4b4d-bb90-2724c0a248cb': {
                    'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        }

        generator = SourceConfigGenerator(service_discovery_config)

        config = generator.generate_from_new_service('unknown',
                                                     s.uuid,
                                                     s.host,
                                                     s.port)

        assert_that(config, equal_to(None))

    def test_generate_with_an_unknown_source(self):
        service_discovery_config = {
            'template_path': None,
            'services': {
                'xivo-confd': {
                    'template': self.template_filename,
                },
            },
            'hosts': {
                'ff791b0e-3d28-4b4d-bb90-2724c0a248cb': {
                    'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        }

        generator = SourceConfigGenerator(service_discovery_config)

        config = generator.generate_from_new_service('xivo-confd',
                                                     'other-uuid',
                                                     s.host,
                                                     s.port)

        assert_that(config, equal_to(None))

    def test_generate_with_a_service(self):
        uuid = 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb'
        service_discovery_config = {
            'template_path': self.template_dir,
            'services': {
                'xivo-confd': {
                    'template': self.template_filename,
                },
            },
            'hosts': {
                uuid: {
                    'uuid': uuid,
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        }

        generator = SourceConfigGenerator(service_discovery_config)

        config = generator.generate_from_new_service('xivo-confd',
                                                     uuid,
                                                     'the-host-name',
                                                     4567)
        expected = {
            'type': 'wazo',
            'name': 'wazo-ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
            'searched_columns': ['firstname', 'lastname'],
            'first_matched_columns': ['exten'],
            'auth': {
                'host': 'the-host-name',
                'port': 9497,
            },
            'confd': {
                'host': 'the-host-name',
                'port': 4567,
                'version': '1.1',
            },
            'format_columns': {
                'number': "{exten}",
                'reverse': "{firstname} {lastname}",
                'voicemail': "{voicemail_number}",
            },
        }

        assert_that(config, equal_to(expected))


class TestProfileConfigUpdater(unittest.TestCase):

    def setUp(self):
        self.config = dict(CONFIG)
        self.source_name = 'wazo-ff791b0e-3d28-4b4d-bb90-2724c0a248cb'

    def test_that_on_service_added_modifies_the_config(self):
        updater = ProfileConfigUpdater(self.config)

        updater.on_service_added(self.source_name, 'xivo-confd')

        expected_lookup_service = {
            'foobar': {'sources': {'source_1': True, 'source_2': True, self.source_name: True}},
            'default': {'sources': {'source_2': True, self.source_name: True}}}
        expected_reverse_service = {
            'foobar': {'sources': {'source_1': True, 'source_2': True, self.source_name: True}},
            'default': {'sources': {'source_2': True}},
            '__switchboard': {'sources': {self.source_name: True}}}
        expected_favorites_service = {
            'foobar': {'sources': {'source_2': True, self.source_name: True}},
            'default': {'sources': {'source_2': True, self.source_name: True}}}

        assert_that(self.config['services']['lookup'],
                    equal_to(expected_lookup_service))
        assert_that(self.config['services']['reverse'],
                    equal_to(expected_reverse_service))
        assert_that(self.config['services']['favorites'],
                    equal_to(expected_favorites_service))

    def test_that_an_unconfigured_consul_service_does_nothing(self):
        original_services = dict(self.config['services'])

        updater = ProfileConfigUpdater(self.config)

        updater.on_service_added(self.source_name, 'xivo-ctid')

        assert_that(self.config['services'], equal_to(original_services))

    def test_that_a_consul_service_with_an_unknown_uuid_does_nothing(self):
        original_services = dict(self.config['services'])

        updater = ProfileConfigUpdater(self.config)

        updater.on_service_added(self.source_name, 'xivo-confd')

        assert_that(self.config['services'], equal_to(original_services))
