# -*- coding: utf-8 -*-

# Copyright (C) 2014-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import unittest

from collections import defaultdict
from hamcrest import assert_that, equal_to, is_, contains
from mock import ANY, patch, Mock, sentinel as s

from xivo_dird.core.source_manager import SourceManager


class TestSourceManager(unittest.TestCase):

    @patch('xivo_dird.core.source_manager.NamedExtensionManager')
    def test_that_load_sources_loads_the_enabled_and_configured_sources(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value
        enabled_backends = [
            'ldap',
            'xivo_phonebook',
        ]
        my_ldap_config = {'type': 'ldap',
                          'name': 'my_ldap'}
        sources_by_type = defaultdict(list)
        sources_by_type['ldap'].append(my_ldap_config)

        manager = SourceManager(enabled_backends, {'sources': {'my_ldap': my_ldap_config}})

        manager.load_sources()

        extension_manager_init.assert_called_once_with(
            namespace='xivo_dird.backends',
            names=enabled_backends,
            name_order=True,
            invoke_on_load=False)
        extension_manager.map.assert_called_once_with(ANY, sources_by_type)

    @patch('xivo_dird.core.source_manager.NamedExtensionManager')
    def test_load_sources_returns_dict_of_sources(self, extension_manager_init):
        enabled_backends = [
            'ldap',
            'xivo_phonebook',
        ]

        manager = SourceManager(enabled_backends, {'sources': {}})
        manager._sources = s.sources

        result = manager.load_sources()

        assert_that(result, equal_to(s.sources))

    def test_load_sources_using_backend_calls_load_on_all_sources_using_this_backend(self):
        config1 = {'type': 'backend', 'name': 'source1'}
        config2 = {'type': 'backend', 'name': 'source2'}
        main_config = {'sources': {'source1': config1, 'source2': config2}}
        configs_by_backend = {'backend': [config1, config2]}
        extension = Mock()
        extension.name = 'backend'
        source1, source2 = extension.plugin.side_effect = Mock(), Mock()
        manager = SourceManager([], main_config)

        manager._load_sources_using_backend(extension, configs_by_backend)

        assert_that(source1.name, equal_to('source1'))
        source1.load.assert_called_once_with({'config': config1, 'main_config': main_config})
        assert_that(source2.name, equal_to('source2'))
        source2.load.assert_called_once_with({'config': config2, 'main_config': main_config})

    def test_load_sources_using_backend_calls_load_on_all_sources_with_exceptions(self):
        config1 = {'type': 'backend', 'name': 'source1'}
        config2 = {'type': 'backend', 'name': 'source2'}
        main_config = {'sources': {'source1': config1, 'source2': config2}}
        configs_by_backend = {'backend': [config1, config2]}
        extension = Mock()
        extension.name = 'backend'
        source1, source2 = extension.plugin.side_effect = Mock(), Mock()
        source1.load.side_effect = RuntimeError
        manager = SourceManager([], main_config)

        manager._load_sources_using_backend(extension, configs_by_backend)

        assert_that(manager._sources.keys(), contains('source2'))
        assert_that(source2.name, equal_to('source2'))
        source2.load.assert_called_once_with({'config': config2, 'main_config': main_config})
