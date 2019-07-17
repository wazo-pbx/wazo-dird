# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import requests
import string

from functools import wraps

from ..constants import VALID_TOKEN_MAIN_TENANT


def random_string(length=10):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def conference_source(**source_args):
    source_args.setdefault('name', random_string())
    source_args.setdefault('auth', {'key_file': '/path/to/key/file'})
    source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.conference_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.conference_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def csv_source(**source_args):
    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            source_args.setdefault('name', random_string())
            source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)
            source_args.setdefault('file', '/tmp/fixture.csv')

            client = self.get_client(source_args['token'])
            source = client.csv_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.csv_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def csv_ws_source(**source_args):
    source_args.setdefault('lookup_url', 'http://example.com/fixture')
    source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.csv_ws_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.csv_ws_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def display(**display_args):
    display_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)
    display_args.setdefault('name', 'display')
    display_args.setdefault('columns', [{'field': 'fn'}])

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(display_args['token'])
            display = client.displays.create(display_args)
            try:
                result = decorated(self, display, *args, **kwargs)
            finally:
                try:
                    self.client.displays.delete(display['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def ldap_source(**source_args):
    source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)
    source_args.setdefault('ldap_uri', 'ldap://example.org')
    source_args.setdefault('ldap_base_dn', 'ou=people,dc=example,dc=org')

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.ldap_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.ldap_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def personal_source(**source_args):
    source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.personal_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.personal_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def phonebook_source(**source_args):
    source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.phonebook_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.phonebook_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator


def wazo_source(**source_args):
    source_args.setdefault('auth', {'key_file': '/path/to/key/file'})
    source_args.setdefault('token', VALID_TOKEN_MAIN_TENANT)

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.wazo_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.wazo_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result

        return wrapper

    return decorator
