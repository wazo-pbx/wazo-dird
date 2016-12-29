# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
# Copyright (C) 2016 Proformatique, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api
from xivo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from xivo_dird.plugins.views.phone.phone_view import PhoneInput, PhoneLookup

TEMPLATE_AASTRA_INPUT = "aastra_input.jinja"
TEMPLATE_AASTRA_RESULTS = "aastra_results.jinja"

CONTENT_TYPE = 'text/xml'
MAX_ITEM_PER_PAGE = 16


class AastraViewPlugin(BaseViewPlugin):

    aastra_input = '/directories/input/<profile>/<xivo_user_uuid>/aastra'
    aastra_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/aastra'

    def load(self, args=None):
        phone_lookup_service = new_phone_lookup_service_from_args(args)
        api.add_resource(PhoneInput, self.aastra_input, endpoint='AastraPhoneInput',
                         resource_class_args=(TEMPLATE_AASTRA_INPUT, CONTENT_TYPE))
        api.add_resource(PhoneLookup, self.aastra_lookup, endpoint='AastraPhoneLookup',
                         resource_class_args=(TEMPLATE_AASTRA_RESULTS, CONTENT_TYPE,
                                              phone_lookup_service, MAX_ITEM_PER_PAGE))