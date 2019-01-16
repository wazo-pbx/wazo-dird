# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests
from functools import wraps


def wazo_source(**source_args):
    def decorator(decorated):

        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            source = self.client.wazo_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    # self.client.wazo_source.delete(result['uuid'])
                    pass
                except requests.HTTPError:
                    pass
            return result
        return wrapper
    return decorator
