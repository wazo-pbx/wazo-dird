# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
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

import logging

from consul import ConsulException
from contextlib import contextmanager
from requests.exceptions import RequestException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo_dird import BaseServicePlugin
from xivo_dird import database
from xivo_dird.core.consul import PERSONAL_CONTACTS_KEY
from xivo_dird.core.consul import PERSONAL_CONTACT_KEY
from xivo_dird.core.consul import dict_from_consul
from xivo_dird.core.consul import dict_to_consul
from xivo_dird.core.consul import new_consul

logger = logging.getLogger(__name__)


UNIQUE_COLUMN = 'id'

Session = scoped_session(sessionmaker())


class PersonalServicePlugin(BaseServicePlugin):

    def load(self, args):
        try:
            config = args['config']
            sources = args['sources']
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

        db_uri = 'postgresql://asterisk:proformatique@localhost/asterisk'
        engine = create_engine(db_uri)
        Session.configure(bind=engine)
        return _PersonalService(config, sources)


class _PersonalService(object):

    class PersonalServiceException(Exception):
        pass

    class NoSuchPersonalContact(ValueError):
        def __init__(self, contact_id):
            message = "No such personal contact: {}".format(contact_id)
            ValueError.__init__(self, message)

    class InvalidPersonalContact(ValueError):
        def __init__(self, errors):
            message = "Invalid personal contact: {}".format(errors)
            ValueError.__init__(self, message)
            self.errors = errors

    def __init__(self, config, sources):
        self._config = config
        self._source = next((source for source in sources.itervalues() if source.backend == 'personal'),
                            DisabledPersonalSource())

    def create_contact(self, contact_infos, token_infos):
        self.validate_contact(contact_infos)
        return database.create_personal_contact(Session(), token_infos['xivo_user_uuid'], contact_infos)

    def get_contact(self, contact_id, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            if not self._contact_exists(consul, token_infos['auth_id'], contact_id):
                raise self.NoSuchPersonalContact(contact_id)
            consul_key = PERSONAL_CONTACT_KEY.format(user_uuid=token_infos['auth_id'],
                                                     contact_uuid=contact_id)
            _, consul_dict = consul.kv.get(consul_key, recurse=True)
        return dict_from_consul(consul_key, consul_dict)

    def edit_contact(self, contact_id, contact_infos, token_infos):
        self.validate_contact(contact_infos)
        with self._consul(token=token_infos['token']) as consul:
            if not self._contact_exists(consul, token_infos['auth_id'], contact_id):
                raise self.NoSuchPersonalContact(contact_id)
        self.remove_contact(contact_id, token_infos)
        return self._create_contact(contact_id, contact_infos, token_infos)

    def remove_contact(self, contact_id, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            if not self._contact_exists(consul, token_infos['auth_id'], contact_id):
                raise self.NoSuchPersonalContact(contact_id)
            consul_key = PERSONAL_CONTACT_KEY.format(user_uuid=token_infos['auth_id'],
                                                     contact_uuid=contact_id)
            consul.kv.delete(consul_key, recurse=True)

    def purge_contacts(self, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            consul_key = PERSONAL_CONTACTS_KEY.format(user_uuid=token_infos['auth_id'],)
            consul.kv.delete(consul_key, recurse=True)

    def list_contacts(self, token_infos):
        contacts = database.list_personal_contacts(Session(), token_infos['xivo_user_uuid'])
        formatted_contacts = self._source.format_contacts(contacts)
        return formatted_contacts

    def list_contacts_raw(self, token_infos):
        return database.list_personal_contacts(Session(), token_infos['xivo_user_uuid'])

    @contextmanager
    def _consul(self, token):
        try:
            yield new_consul(self._config, token=token)
        except ConsulException as e:
            raise self.PersonalServiceException('Error from Consul: {}'.format(str(e)))
        except RequestException as e:
            raise self.PersonalServiceException('Error while connecting to Consul: {}'.format(str(e)))

    def _contact_exists(self, consul, user_uuid, contact_id):
        consul_key = PERSONAL_CONTACT_KEY.format(user_uuid=user_uuid,
                                                 contact_uuid=contact_id)
        _, result = consul.kv.get(consul_key, keys=True)
        return result is not None

    def _create_contact(self, contact_id, contact_infos, token_infos):
        result = dict(contact_infos)
        result[UNIQUE_COLUMN] = contact_id
        with self._consul(token=token_infos['token']) as consul:
            prefix = PERSONAL_CONTACT_KEY.format(user_uuid=token_infos['auth_id'],
                                                 contact_uuid=contact_id)
            for consul_key, value in dict_to_consul(prefix, result).iteritems():
                consul.kv.put(consul_key, value)
        return result

    @staticmethod
    def validate_contact(contact_infos):
        errors = []

        if any(not hasattr(key, 'encode') for key in contact_infos):
            errors.append('all keys must be strings')

        if any(not hasattr(value, 'encode') for value in contact_infos.itervalues()):
            errors.append('all values must be strings')

        if errors:
            raise _PersonalService.InvalidPersonalContact(errors)
        # from here we assume we have strings

        if '.' in contact_infos:
            errors.append('key `.` is invalid')

        if any((('..' in key) for key in contact_infos)):
            errors.append('.. is forbidden in keys')

        if any('//' in key for key in contact_infos):
            errors.append('// is forbidden in keys')

        if any(key.startswith('/') for key in contact_infos):
            errors.append('key must not start with /')

        if any(key.endswith('/') for key in contact_infos):
            errors.append('key must not end with /')

        if any(key.startswith('./') for key in contact_infos):
            errors.append('key must not start with ./')

        if any(key.endswith('/.') for key in contact_infos):
            errors.append('key must not end with /.')

        if any('/./' in key for key in contact_infos):
            errors.append('key must not contain /./')

        try:
            for key in contact_infos:
                key.encode('ascii')
        except UnicodeEncodeError:
            errors.append('key must contain only ASCII characters')

        if errors:
            raise _PersonalService.InvalidPersonalContact(errors)


class DisabledPersonalSource(object):
    def list(self, _source_entry_ids, _token_infos):
        return []
