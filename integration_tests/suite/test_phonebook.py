# -*- coding: utf-8 -*-
# Copyright (C) 2016 Avencall
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

from mock import ANY
from hamcrest import assert_that, contains_inanyorder, equal_to

from .base_dird_integration_test import BaseDirdIntegrationTest


class TestPhonebookCRUD(BaseDirdIntegrationTest):

    asset = 'phonebook_only'

    def test_all(self):
        tenant_1, tenant_2 = 'default', 'malicious'
        phonebook_1_body = {'name': 'integration',
                            'description': 'The integration test phonebook'}
        phonebook_1 = self.post_phonebook(tenant_1, phonebook_1_body)
        assert_that(self.get_phonebook(tenant_1, phonebook_1['id']), equal_to(phonebook_1))

        expected = dict(phonebook_1_body)
        expected['id'] = ANY
        assert_that(phonebook_1, equal_to(expected))

        phonebook_2 = self.post_phonebook(tenant_1, {'name': 'second'})

        assert_that(self.list_phonebooks(tenant_1), contains_inanyorder(phonebook_1, phonebook_2))

        self.delete_phonebook(tenant_2, phonebook_2['id'])
        assert_that(self.list_phonebooks(tenant_1), contains_inanyorder(phonebook_1, phonebook_2))

        self.delete_phonebook(tenant_1, phonebook_2['id'])
        assert_that(self.list_phonebooks(tenant_1), contains_inanyorder(phonebook_1))

        alice = self.post_phonebook_contact(tenant_1, phonebook_1['id'], {'firstname': 'alice'})
        assert_that(self.get_phonebook_contact(tenant_1, phonebook_1['id'], alice['id']),
                    equal_to(alice))
        bob = self.post_phonebook_contact(tenant_1, phonebook_1['id'], {'firstname': 'bob'})
        assert_that(self.list_phonebook_contacts(tenant_1, phonebook_1['id']),
                    contains_inanyorder(alice, bob))
