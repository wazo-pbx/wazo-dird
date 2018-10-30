# Copyright (C) 2015-2016 Avencall
# SPDX-License-Identifier: GPL-3.0+

import logging

from xivo import auth_verifier
from xivo_auth_client import Client

logger = logging.getLogger(__name__)

auth_config = None
auth_client = None
required_acl = auth_verifier.required_acl


def set_auth_config(config):
    global auth_config
    auth_config = config


def client():
    global auth_client
    if not auth_client:
        auth_client = Client(**auth_config)
    return auth_client
