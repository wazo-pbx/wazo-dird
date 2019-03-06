# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import kombu

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.auth.events import TenantCreatedEvent

from wazo_dird import (
    BaseServicePlugin,
    database,
)

logger = logging.getLogger(__name__)


class SourceServicePlugin(BaseServicePlugin):

    def load(self, dependencies):
        bus = dependencies['bus']
        self._config = dependencies['config']
        db_uri = self._config['db_uri']
        Session = self._new_db_session(db_uri)
        return _SourceService(database.SourceCRUD(Session), bus, db_uri)

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _SourceService:

    _QUEUE = kombu.Queue(
        exchange=kombu.Exchange('xivo', type='topic'),
        routing_key='auth.tenants.*.created',
        exclusive=True,
    )
    _personal_source_body = {
        'format_columns': {
            'phone': '{number}',
            'name': '{firstname} {lastname}',
            'phone_mobile': '{mobile}',
            'reverse': '{firstname} {lastname}',
        },
        'searched_columns': ['firstname', 'lastname', 'number', 'mobile', 'fax'],
        'first_matched_columns': ['number', 'mobile'],
    }
    _wazo_source_body = {
        'auth': {
            'host': 'localhost',
            'port': 9497,
            'verify_certificate': '/usr/share/xivo-certs/server.crt',
            'key_file': '/var/lib/wazo-auth-keys/wazo-dird-wazo-backend-key.yml',
            'version': '0.1',
        },
        'confd': {
            'host': 'localhost',
            'port': 9486,
            'https': True,
            'verify_certificate': '/usr/share/xivo-certs/server.crt',
            'version': '1.1',
        },
        'format_columns': {
            'phone': '{exten}',
            'name': '{firstname} {lastname}',
        },
        'searched_columns': ['firstname', 'lastname', 'exten'],
        'first_matched_columns': [],
    }
    _office_365_source_body = {
        'auth': {
            'host': 'localhost',
            'port': 9497,
            'verify_certificate': '/usr/share/xivo-certs/server.crt',
            'key_file': '/var/lib/wazo-auth-keys/wazo-dird-wazo-backend-key.yml',
            'version': '0.1',
        },
        'endpoint': 'https://graph.microsoft.com/v1.0/me/contacts',
        'format_columns': {
            'name': '{firstname} {lastname}',
            'phone_mobile': '{mobile}',
            'reverse': '{firstname} {lastname}',
        },
        'searched_columns': ['firstname', 'lastname', 'mobile', 'number'],
        'first_matched_columns': ['mobile', 'number'],
    }

    def __init__(self, crud, bus, db_uri):
        self._source_crud = crud
        self._db_uri = db_uri
        bus.add_consumer(self._QUEUE, self._on_new_tenant)

    def count(self, backend, visible_tenants, **list_params):
        return self._source_crud.count(backend, visible_tenants, **list_params)

    def create(self, backend, **body):
        return self._source_crud.create(backend, body)

    def delete(self, backend, source_uuid, visible_tenants):
        return self._source_crud.delete(backend, source_uuid, visible_tenants)

    def edit(self, backend, source_uuid, visible_tenants, body):
        return self._source_crud.edit(backend, source_uuid, visible_tenants, body)

    def get(self, backend, source_uuid, visible_tenants):
        return self._source_crud.get(backend, source_uuid, visible_tenants)

    def get_by_uuid(self, uuid):
        return self._source_crud.get_by_uuid(uuid)

    def list_(self, backend, visible_tenants, **list_params):
        return self._source_crud.list_(backend, visible_tenants, **list_params)

    def _add_source(self, backend, body):
        try:
            self.create(backend, **body)
        except Exception as e:
            logger.info('failed to create %s source %s', backend, e)

    def _add_personal_source(self, tenant_uuid, name):
        backend = 'personal'
        body = dict(self._personal_source_body)
        body['name'] = 'auto_{}_{}'.format(backend, name)
        body['tenant_uuid'] = tenant_uuid
        body['db_uri'] = self._db_uri
        self._add_source(backend, body)

    def _add_wazo_user_source(self, tenant_uuid, name):
        backend = 'wazo'
        body = dict(self._wazo_source_body)
        body['name'] = 'auto_{}_{}'.format(backend, name)
        body['tenant_uuid'] = tenant_uuid
        self._add_source(backend, body)

    def _add_office365_source(self, tenant_uuid, name):
        backend = 'office365'
        body = dict(self._personal_source_body)
        body['name'] = 'auto_{}_{}'.format(backend, name)
        body['tenant_uuid'] = tenant_uuid
        body['db_uri'] = self._db_uri
        self._add_source(backend, body)

    def _auto_create_sources(self, tenant_uuid, name):
        logger.info('creating sources for tenant "%s"', name)
        self._add_personal_source(tenant_uuid, name)
        self._add_wazo_user_source(tenant_uuid, name)
        self._add_office365_source(tenant_uuid, name)

    def _on_new_tenant(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, TenantCreatedEvent)
            body = event.marshal()
        except (InvalidMessage, KeyError):
            logger.info('Ignoring the following malformed bus message: %s', body)
        else:
            self._auto_create_sources(body['uuid'], body['name'])
        finally:
            message.ack()