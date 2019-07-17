# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from wazo_dird import BaseViewPlugin

from .http import SourceResource

logger = logging.getLogger(__name__)


class SourceViewPlugin(BaseViewPlugin):
    def load(self, dependencies):
        api = dependencies['api']
        profile_service = dependencies['services']['profile']
        args = (profile_service,)
        api.add_resource(
            SourceResource, '/directories/<profile>/sources', resource_class_args=args
        )
