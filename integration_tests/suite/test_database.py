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

import functools
import uuid
import os
import unittest

from collections import defaultdict
from contextlib import contextmanager, nested
from hamcrest import (assert_that,
                      any_of,
                      calling,
                      contains,
                      contains_inanyorder,
                      empty,
                      equal_to,
                      has_item,
                      has_items,
                      not_,
                      raises)
from mock import ANY

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, func

from xivo_dird import database

from .base_dird_integration_test import BaseDirdIntegrationTest

Session = sessionmaker()


def new_uuid():
    return str(uuid.uuid4())


def expected(contact):
    result = {'id': ANY}
    result.update(contact)
    return result


def with_user_uuid(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        user_uuid = new_uuid()
        user = database.User(xivo_user_uuid=user_uuid)
        session = Session()
        session.add(user)
        session.commit()
        result = f(self, user_uuid, *args, **kwargs)
        session.query(database.User).filter(database.User.xivo_user_uuid == user_uuid).delete()
        session.commit()
        return result
    return wrapped


class DBStarter(BaseDirdIntegrationTest):

    asset = 'database'


def setup():
    DBStarter.setUpClass()
    db_uri = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:15432')
    engine = create_engine(db_uri)
    database.Base.metadata.bind = engine
    database.Base.metadata.reflect()
    database.Base.metadata.drop_all()
    database.Base.metadata.create_all()


def teardown():
    DBStarter.tearDownClass()


class _BaseTest(unittest.TestCase):

    def setUp(self):
        self._contact_1 = {u'firtname': u'Finley',
                           u'lastname': u'Shelley',
                           u'number': u'5555551111'}
        self._contact_2 = {u'firstname': u'Cédric',
                           u'lastname': u'Ora',
                           u'number': u'5555550001'}
        self._contact_3 = {u'firstname': u'Foo',
                           u'lastname': u'Bar',
                           u'number': u'5555550001'}

    @property
    def contact_1(self):
        return dict(self._contact_1)

    @property
    def contact_2(self):
        return dict(self._contact_2)

    @property
    def contact_3(self):
        return dict(self._contact_3)

    def _insert_personal_contacts(self, xivo_user_uuid, *contacts):
        ids = []
        session = Session()
        for contact in contacts:
            hash_ = database.compute_contact_hash(contact)
            dird_contact = database.Contact(user_uuid=xivo_user_uuid, hash=hash_)
            session.add(dird_contact)
            session.flush()
            ids.append(dird_contact.uuid)
            for name, value in contact.iteritems():
                field = database.ContactFields(name=name, value=value, contact_uuid=dird_contact.uuid)
                session.add(field)
        session.commit()
        return ids

    def _list_contacts(self):
        s = Session()
        contacts = defaultdict(dict)
        for field in s.query(database.ContactFields).all():
            contacts[field.contact_uuid][field.name] = field.value
        return contacts.values()


class _BasePhonebookCRUDTest(_BaseTest):

    def setUp(self):
        super(_BasePhonebookCRUDTest, self).setUp()
        self._crud = database.PhonebookCRUD(Session)

    @contextmanager
    def _new_phonebook(self, tenant, name, description=None, delete=True):
        body = {'name': name}
        if description:
            body['description'] = description

        phonebook = self._crud.create(tenant, body)
        yield phonebook
        if delete:
            self._crud.delete(tenant, phonebook['id'])


class TestPhonebookCRUDCount(_BasePhonebookCRUDTest):

    def test_count(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a'),
                    self._new_phonebook(tenant, 'b'),
                    self._new_phonebook(tenant, 'c')) as phonebooks:
            result = self._crud.count(tenant)

        assert_that(result, equal_to(len(phonebooks)))

    def test_that_an_unknown_tenant_returns_zero(self):
        result = self._crud.count('unknown')

        assert_that(result, equal_to(0))

    def test_that_phonebooks_from_others_are_not_counted(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a'),
                    self._new_phonebook(tenant, 'b'),
                    self._new_phonebook('other', 'c')) as phonebooks:
            result = self._crud.count(tenant)

        assert_that(result, equal_to(len(phonebooks) - 1))

    def test_that_only_matching_phonebooks_are_counted(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'ab'),
                    self._new_phonebook(tenant, 'bc'),
                    self._new_phonebook(tenant, 'cd')):
            result = self._crud.count(tenant, search='b')

        assert_that(result, equal_to(2))


class TestPhonebookCRUDCreate(_BasePhonebookCRUDTest):

    def tearDown(self):
        session = Session()
        for phonebook in session.query(database.Phonebook).all():
            session.delete(phonebook)
        session.commit()
        super(TestPhonebookCRUDCreate, self).tearDown()

    def test_that_create_creates_a_phonebook_and_a_tenant(self):
        tenant = 'default'
        body = {'name': 'main',
                'description': 'The main phonebook for "default"'}
        expected = dict(body)
        expected['id'] = ANY

        result = self._crud.create(tenant, body)

        assert_that(result, equal_to(expected))

    def test_that_create_without_name_fails(self):
        tenant = 'default'

        assert_that(calling(self._crud.create).with_args(tenant, None),
                    raises(Exception))
        assert_that(calling(self._crud.create).with_args(tenant, {}),
                    raises(Exception))
        assert_that(calling(self._crud.create).with_args(tenant, {'name': ''}),
                    raises(Exception))

    def test_that_create_without_description(self):
        tenant = 'default'
        body = {'name': 'nodesc'}
        expected = {'id': ANY,
                    'name': 'nodesc',
                    'description': None}

        result = self._crud.create(tenant, body)

        assert_that(result, equal_to(expected))

    def test_that_create_with_invalid_fields_raises(self):
        tenant = 'default'
        body = {'name': 'nodesc', 'foo': 'bar'}

        assert_that(calling(self._crud.create).with_args(tenant, body),
                    raises(TypeError))

    def test_that_create_raises_if_two_phonebook_have_the_same_name_and_tenant(self):
        tenant = 'default'
        body = {'name': 'new'}
        self._crud.create(tenant, body)

        assert_that(calling(self._crud.create).with_args(tenant, body),
                    raises(database.DuplicatedPhonebookException))

    def test_that_duplicate_tenants_are_not_created(self):
        tenant = 'default'

        self._crud.create(tenant, {'name': 'first'})
        self._crud.create(tenant, {'name': 'second'})

        session = Session()
        tenant_count = session.query(func.count(database.Tenant.id)).filter(
            database.Tenant.name == tenant).scalar()
        assert_that(tenant_count, equal_to(1))


class TestPhonebookCRUDDelete(_BasePhonebookCRUDTest):

    def test_that_delete_removes_the_phonebook(self):
        tenant = 'default'
        with self._new_phonebook(tenant, 'first', delete=False) as phonebook:
            self._crud.delete(tenant, phonebook['id'])

        phonebook_count = (Session()
                           .query(func.count(database.Phonebook.id))
                           .filter(database.Phonebook.id == phonebook['id'])
                           .scalar())
        assert_that(phonebook_count, equal_to(0))

    def test_that_deleting_an_unknown_phonebook_raises(self):
        assert_that(calling(self._crud.delete).with_args('tenant', 42),
                    raises(database.NoSuchPhonebook))

    def test_that_deleting_another_tenant_phonebook_is_not_possible(self):
        tenant_a = 'a'
        tenant_b = 'b'

        with self._new_phonebook(tenant_a, 'main') as phonebook:
            assert_that(calling(self._crud.delete).with_args(tenant_b, phonebook['id']),
                        raises(database.NoSuchPhonebook))

    def test_that_tenants_are_not_created_on_delete(self):
        tenant_a = 'real'
        tenant_b = 'unknown'

        with self._new_phonebook(tenant_a, 'a') as phonebook:
            try:
                self._crud.delete(tenant_b, phonebook['id'])
            except database.NoSuchPhonebook:
                pass  # as expected

        tenant_created = Session().query(
            func.count(database.Tenant.id)).filter(database.Tenant.name == tenant_b).scalar() > 0

        assert_that(tenant_created, equal_to(False))


class TestPhonebookCRUDEdit(_BasePhonebookCRUDTest):

    def test_that_edit_changes_the_phonebook(self):
        tenant = 'tenant'

        with self._new_phonebook(tenant, 'name') as phonebook:
            new_body = {'name': 'new_name', 'description': 'lol'}
            result = self._crud.edit(tenant, phonebook['id'], new_body)

        expected = dict(new_body)
        expected['id'] = phonebook['id']

        assert_that(result, equal_to(expected))

    def test_that_invalid_keys_raise_an_exception(self):
        tenant = 'tenant'

        with self._new_phonebook(tenant, 'unknown fields') as phonebook:
            new_body = {'foo': 'bar'}

            assert_that(calling(self._crud.edit).with_args(tenant, phonebook['id'], new_body),
                        raises(TypeError))

    def test_that_editing_an_unknown_phonebook_raises(self):
        tenant = 'tenant'

        assert_that(calling(self._crud.edit).with_args(tenant, 42, {'name': 'test'}),
                    raises(database.NoSuchPhonebook))

    def test_that_editing_a_phonebook_from_another_tenant_raises(self):
        with nested(self._new_phonebook('tenant_a', 'a'),
                    self._new_phonebook('tenant_b', 'b')) as (phonebook_a, _):
            assert_that(calling(self._crud.edit).with_args('tenant_b', phonebook_a['id'], {'name': 'foo'}),
                        raises(database.NoSuchPhonebook))


class TestPhonebookCRUDGet(_BasePhonebookCRUDTest):

    def test_that_get_returns_the_phonebook(self):
        with self._new_phonebook('tenant', 'a') as phonebook:
            result = self._crud.get('tenant', phonebook['id'])

        assert_that(result, equal_to(phonebook))

    def test_that_get_with_an_unknown_id_raises(self):
        assert_that(calling(self._crud.get).with_args('tenant', 42),
                    raises(database.NoSuchPhonebook))

    def test_that_get_from_another_tenant_raises(self):
        with self._new_phonebook('tenant_a', 'a') as phonebook:
            assert_that(calling(self._crud.get).with_args('tenant_b', phonebook['id']),
                        raises(database.NoSuchPhonebook))


class TestPhonebookCRUDList(_BasePhonebookCRUDTest):

    def test_that_all_phonebooks_are_listed(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a'),
                    self._new_phonebook(tenant, 'b'),
                    self._new_phonebook(tenant, 'c')) as (a, b, c):
            result = self._crud.list(tenant)
        assert_that(result, contains_inanyorder(a, b, c))

    def test_that_phonebooks_from_others_are_not_listed(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a'),
                    self._new_phonebook(tenant, 'b'),
                    self._new_phonebook('not_t', 'c')) as (a, b, _):
            result = self._crud.list(tenant)
        assert_that(result, contains_inanyorder(a, b))

    def test_that_no_phonebooks_returns_an_empty_list(self):
        result = self._crud.list('t')

        assert_that(result, empty())

    def test_that_phonebooks_can_be_ordered(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a', description='z'),
                    self._new_phonebook(tenant, 'b', description='b'),
                    self._new_phonebook(tenant, 'c')) as (a, b, c):
            result = self._crud.list(tenant, order='description')
        assert_that(result, contains_inanyorder(b, a, c))

    def test_that_phonebooks_order_with_invalid_field_raises(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a', description='z'),
                    self._new_phonebook(tenant, 'b', description='b'),
                    self._new_phonebook(tenant, 'c')) as (a, b, c):
            assert_that(calling(self._crud.list).with_args(tenant, order='foo'),
                        raises(TypeError))

    def test_that_phonebooks_can_be_ordered_in_any_order(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a', description='z'),
                    self._new_phonebook(tenant, 'b', description='b'),
                    self._new_phonebook(tenant, 'c')) as (a, b, c):
            result = self._crud.list(tenant, order='description', direction='desc')
        assert_that(result, contains_inanyorder(a, b, c))

    def test_that_phonebooks_can_be_limited(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a'),
                    self._new_phonebook(tenant, 'b'),
                    self._new_phonebook(tenant, 'c')) as (a, b, c):
            result = self._crud.list(tenant, limit=2)
        assert_that(result, contains_inanyorder(a, b))

    def test_that_an_offset_can_be_supplied(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'a'),
                    self._new_phonebook(tenant, 'b'),
                    self._new_phonebook(tenant, 'c')) as (a, b, c):
            result = self._crud.list(tenant, offset=2)
        assert_that(result, contains_inanyorder(c))

    def test_that_list_only_returns_matching_phonebooks(self):
        tenant = 't'
        with nested(self._new_phonebook(tenant, 'aa', description='foobar'),
                    self._new_phonebook(tenant, 'bb'),
                    self._new_phonebook(tenant, 'cc')) as (a, b, c):
            result = self._crud.list(tenant, search='b')

        assert_that(result, contains_inanyorder(a, b))


class TestPhonebookContactCRUDCreate(_BaseTest):

    def setUp(self):
        super(TestPhonebookContactCRUDCreate, self).setUp()
        self._tenant = 'the-tenant'
        self._crud = database.PhonebookContactCRUD(Session)
        self._phonebook_crud = database.PhonebookCRUD(Session)
        body = {'name': 'main', 'description': 'the integration test phonebook'}
        self._phonebook = self._phonebook_crud.create(self._tenant, body)
        self._phonebook_id = self._phonebook['id']
        self._body = {'firstname': 'Foo',
                      'lastname': 'bar',
                      'number': '5555555555'}

    def tearDown(self):
        self._phonebook_crud.delete(self._tenant, self._phonebook_id)
        super(TestPhonebookContactCRUDCreate, self).tearDown()

    def test_that_a_phonebook_contact_can_be_created(self):
        result = self._crud.create(self._tenant, self._phonebook_id, self._body)

        expected = dict(self._body)
        expected['id'] = ANY
        assert_that(result, equal_to(expected))
        assert_that(self._list_contacts(), has_item(expected))

    def test_that_duplicated_contacts_cannot_be_created(self):
        self._crud.create(self._tenant, self._phonebook_id, self._body)
        assert_that(calling(self._crud.create).with_args(self._tenant, self._phonebook_id, self._body),
                    raises(database.DuplicatedContactException))

    def test_that_duplicates_can_happen_in_different_phonebooks(self):
        phonebook_2 = self._phonebook_crud.create(self._tenant, {'name': 'second'})

        contact_1 = self._crud.create(self._tenant, self._phonebook_id, self._body)
        contact_2 = self._crud.create(self._tenant, phonebook_2['id'], self._body)

        assert_that(self._list_contacts(), has_items(contact_1, contact_2))

    def test_that_a_tenant_can_only_create_in_his_phonebook(self):
        assert_that(calling(self._crud.create).with_args('not-the-tenant', self._phonebook_id, self._body),
                    raises(database.NoSuchPhonebook))

    def test_that_deleting_contact_removes_it(self):
        contact = self._crud.create(self._tenant, self._phonebook_id, self._body)

        self._crud.delete(self._tenant, self._phonebook_id, contact['id'])

        assert_that(self._list_contacts(), not_(has_item(contact)))

    def test_that_deleting_with_another_tenant_does_not_work(self):
        contact = self._crud.create(self._tenant, self._phonebook_id, self._body)

        assert_that(calling(self._crud.delete).with_args('not-the-tenant', self._phonebook_id, contact['id']),
                    raises(database.NoSuchPhonebook))
        assert_that(self._list_contacts(), has_item(contact))

    def test_that_deleting_an_unknown_contact_raises(self):
        unknown_contact_uuid = new_uuid()

        assert_that(calling(self._crud.delete)
                    .with_args(self._tenant, self._phonebook_id, unknown_contact_uuid),
                    raises(database.NoSuchContact))

    def test_that_get_returns_the_contact(self):
        contact = self._crud.create(self._tenant, self._phonebook_id, self._body)

        result = self._crud.get(self._tenant, self._phonebook_id, contact['id'])

        assert_that(result, equal_to(contact))

    def test_that_get_wont_work_with_the_wrong_phonebook_id(self):
        other_phonebook = self._phonebook_crud.create(self._tenant, {'name': 'other'})
        contact = self._crud.create(self._tenant, self._phonebook_id, self._body)

        assert_that(calling(self._crud.get).with_args(self._tenant, other_phonebook['id'], contact['id']),
                    raises(database.NoSuchContact))

    def test_that_get_wont_work_with_the_wrong_tenant(self):
        contact = self._crud.create(self._tenant, self._phonebook_id, self._body)

        assert_that(calling(self._crud.get).with_args('not-the-tenant', self._phonebook_id, contact['id']),
                    raises(database.NoSuchPhonebook))


class TestContactCRUD(_BaseTest):

    def setUp(self):
        super(TestContactCRUD, self).setUp()
        self._crud = database.PersonalContactCRUD(Session)

    def test_that_create_personal_contact_creates_a_contact_and_the_owner(self):
        owner = new_uuid()

        result = self._crud.create_personal_contact(owner, self.contact_1)
        assert_that(result, equal_to(expected(self.contact_1)))

        contact_list = self._crud.list_personal_contacts(owner)
        assert_that(contact_list, contains(expected(self.contact_1)))

    @with_user_uuid
    def test_that_create_personal_contact_creates_a_contact_with_an_existing_owner(self, xivo_user_uuid):
        result = self._crud.create_personal_contact(xivo_user_uuid, self.contact_1)
        assert_that(result, equal_to(expected(self.contact_1)))

        contact_list = self._crud.list_personal_contacts(xivo_user_uuid)
        assert_that(contact_list, contains(expected(self.contact_1)))

    @with_user_uuid
    def test_that_personal_contacts_are_unique(self, xivo_user_uuid):
        self._crud.create_personal_contact(xivo_user_uuid, self.contact_1)
        assert_that(calling(self._crud.create_personal_contact).with_args(xivo_user_uuid, self.contact_1),
                    raises(database.DuplicatedContactException))

    @with_user_uuid
    def test_that_personal_contacts_remain_unique(self, xivo_user_uuid):
        contact_1_uuid = self._crud.create_personal_contact(xivo_user_uuid, self.contact_1)['id']
        self._crud.create_personal_contact(xivo_user_uuid, self.contact_2)['id']

        assert_that(calling(self._crud.edit_personal_contact).with_args(xivo_user_uuid, contact_1_uuid, self.contact_2),
                    raises(database.DuplicatedContactException))
        contact_list = self._crud.list_personal_contacts(xivo_user_uuid)
        assert_that(contact_list, contains_inanyorder(expected(self.contact_1), expected(self.contact_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_personal_contacts_can_be_duplicated_between_users(self, user_uuid_1, user_uuid_2):
        contact_1_uuid = self._crud.create_personal_contact(user_uuid_1, self.contact_1)['id']
        contact_2_uuid = self._crud.create_personal_contact(user_uuid_2, self.contact_1)['id']

        assert_that(contact_1_uuid, not_(equal_to(contact_2_uuid)))

    @with_user_uuid
    def test_get_personal_contact(self, xivo_user_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(xivo_user_uuid,
                                                             self.contact_1,
                                                             self.contact_2,
                                                             self.contact_3)

        result = self._crud.get_personal_contact(xivo_user_uuid, contact_uuid)

        assert_that(result, equal_to(expected(self.contact_1)))

    @with_user_uuid
    @with_user_uuid
    def test_get_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(user_1_uuid, self.contact_1, self.contact_2, self.contact_3)

        assert_that(calling(self._crud.get_personal_contact).with_args(user_2_uuid, contact_uuid),
                    raises(database.NoSuchContact))

    @with_user_uuid
    def test_delete_personal_contact(self, xivo_user_uuid):
        contact_uuid, = self._insert_personal_contacts(xivo_user_uuid, self.contact_1)

        self._crud.delete_personal_contact(xivo_user_uuid, contact_uuid)

        assert_that(calling(self._crud.get_personal_contact).with_args(xivo_user_uuid, contact_uuid),
                    raises(database.NoSuchContact))

    @with_user_uuid
    @with_user_uuid
    def test_delete_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, = self._insert_personal_contacts(user_1_uuid, self.contact_1)

        assert_that(calling(self._crud.delete_personal_contact).with_args(user_2_uuid, contact_uuid),
                    raises(database.NoSuchContact))

    @with_user_uuid
    @with_user_uuid
    def test_delete_all_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid_1, = self._insert_personal_contacts(user_1_uuid, self.contact_1)
        contact_uuid_2, contact_uuid_3 = self._insert_personal_contacts(user_2_uuid, self.contact_2, self.contact_3)

        self._crud.delete_all_personal_contacts(user_2_uuid)

        assert_that(calling(self._crud.get_personal_contact).with_args(user_1_uuid, contact_uuid_1),
                    not_(raises(database.NoSuchContact)))
        assert_that(calling(self._crud.get_personal_contact).with_args(user_2_uuid, contact_uuid_2),
                    raises(database.NoSuchContact))
        assert_that(calling(self._crud.get_personal_contact).with_args(user_2_uuid, contact_uuid_3),
                    raises(database.NoSuchContact))


class TestFavoriteCrud(_BaseTest):

    def setUp(self):
        super(TestFavoriteCrud, self).setUp()
        self._crud = database.FavoriteCRUD(Session)

    def test_that_create_creates_a_favorite(self):
        xivo_user_uuid = new_uuid()
        source_name = 'foobar'
        contact_id = 'the-contact-id'

        favorite = self._crud.create(xivo_user_uuid, source_name, contact_id)

        assert_that(favorite.user_uuid, equal_to(xivo_user_uuid))
        assert_that(favorite.contact_id, equal_to(contact_id))

        assert_that(self._user_exists(xivo_user_uuid))
        assert_that(self._favorite_exists(xivo_user_uuid, source_name, contact_id))

    @with_user_uuid
    def test_that_creating_the_same_favorite_raises(self, xivo_user_uuid):
        source, contact_id = 'source', 'the-contact-id'
        self._crud.create(xivo_user_uuid, source, contact_id)
        assert_that(calling(self._crud.create).with_args(xivo_user_uuid, source, contact_id),
                    raises(database.DuplicatedFavoriteException))

    @with_user_uuid
    @with_user_uuid
    def test_get(self, user_1, user_2):
        self._crud.create(user_1, 's1', '1')
        self._crud.create(user_1, 's2', '1')
        self._crud.create(user_1, 's1', '42')
        self._crud.create(user_2, 's1', '42')
        self._crud.create(user_2, 's3', '1')

        fav_1 = self._crud.get(user_1)
        fav_2 = self._crud.get(user_2)

        assert_that(fav_1, contains_inanyorder(
            ('s1', '1'),
            ('s2', '1'),
            ('s1', '42'),
        ))
        assert_that(fav_2, contains_inanyorder(
            ('s1', '42'),
            ('s3', '1'),
        ))

    @with_user_uuid
    def test_that_delete_removes_a_favorite(self, xivo_user_uuid):
        self._crud.create(xivo_user_uuid, 'source', 'the-contact-id')

        self._crud.delete(xivo_user_uuid, 'source', 'the-contact-id')

        assert_that(self._favorite_exists(xivo_user_uuid, 'source', 'the-contact-id'),
                    equal_to(False))

    @with_user_uuid
    @with_user_uuid
    def test_that_delete_does_not_remove_favorites_from_other_users(self, user_1, user_2):
        self._crud.create(user_2, 'source', 'the-contact-id')

        assert_that(calling(self._crud.delete).with_args(user_1, 'source', 'the-contact-id'),
                    raises(database.NoSuchFavorite))

        assert_that(self._favorite_exists(user_2, 'source', 'the-contact-id'))

    @with_user_uuid
    def test_that_delete_raises_if_not_found(self, xivo_user_uuid):
        assert_that(calling(self._crud.delete).with_args(xivo_user_uuid, 'source', 'the-contact-id'),
                    raises(database.NoSuchFavorite))

    @with_user_uuid
    def test_that_delete_from_an_unknown_source_raises(self, xivo_user_uuid):
        self._crud.create(xivo_user_uuid, 'source', 'the-contact-id')

        assert_that(calling(self._crud.delete).with_args(xivo_user_uuid, 'not-source', 'the-contact-id'),
                    raises(database.NoSuchFavorite))

    def _user_exists(self, xivo_user_uuid):
        session = Session()

        user_uuid = session.query(database.User.xivo_user_uuid).filter(
            database.User.xivo_user_uuid == xivo_user_uuid
        ).scalar()

        return user_uuid is not None

    def _favorite_exists(self, xivo_user_uuid, source_name, contact_id):
        session = Session()

        favorite = (session.query(database.Favorite)
                    .join(database.Source)
                    .join(database.User)
                    .filter(and_(database.User.xivo_user_uuid == xivo_user_uuid,
                                 database.Source.name == source_name,
                                 database.Favorite.contact_id == contact_id))).first()

        return favorite is not None


class TestPersonalContactSearchEngine(_BaseTest):

    @with_user_uuid
    def test_that_find_first_returns_a_contact(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, first_match_columns=['number'])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2, self.contact_3)

        result = engine.find_first_personal_contact(xivo_user_uuid, u'5555550001')

        assert_that(result, contains(any_of(expected(self.contact_2), expected(self.contact_3))))

    @with_user_uuid
    def test_that_listing_personal_contacts_returns_the_searched_contacts(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        ids = self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.list_personal_contacts(xivo_user_uuid, ids)
        assert_that(result, contains_inanyorder(expected(self.contact_1), expected(self.contact_2)))

        result = engine.list_personal_contacts(xivo_user_uuid, ids[:1])
        assert_that(result, contains(expected(self.contact_1)))

        result = engine.list_personal_contacts(xivo_user_uuid, ids[1:])
        assert_that(result, contains(expected(self.contact_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_listing_personal_contacts_only_the_users_contact(self, uuid_1, uuid_2):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        ids_1 = self._insert_personal_contacts(uuid_1, self.contact_1, self.contact_2)
        ids_2 = self._insert_personal_contacts(uuid_2, self.contact_1, self.contact_3)

        result = engine.list_personal_contacts(uuid_1, ids_1)
        assert_that(result, contains_inanyorder(expected(self.contact_1), expected(self.contact_2)))

        result = engine.list_personal_contacts(uuid_2, ids_2)
        assert_that(result, contains_inanyorder(expected(self.contact_1), expected(self.contact_3)))

        result = engine.list_personal_contacts(uuid_1, ids_2)
        assert_that(result, empty())

        result = engine.list_personal_contacts(uuid_2, ids_1)
        assert_that(result, empty())

    @with_user_uuid
    def test_that_searching_for_a_contact_returns_its_fields(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(xivo_user_uuid, u'ced')
        assert_that(result, contains(expected(self.contact_2)))

        result = engine.find_personal_contacts(xivo_user_uuid, u'céd')
        assert_that(result, contains(expected(self.contact_2)))

    @with_user_uuid
    def test_that_find_searches_only_in_searched_columns(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['lastname'])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(xivo_user_uuid, u'ced')

        assert_that(result, empty())

    @with_user_uuid
    def test_that_no_searched_columns_does_not_search(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=[])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(xivo_user_uuid, u'ced')

        assert_that(result, empty())
