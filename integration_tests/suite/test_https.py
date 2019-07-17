# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from hamcrest import assert_that, contains_string

from .helpers.base import DirdAssetRunningTestCase


class TestHTTPSMissingCertificate(DirdAssetRunningTestCase):

    asset = 'no-ssl-certificate'

    def test_given_inexisting_SSL_certificate_when_dird_starts_then_dird_stops(self):
        for _ in range(5):
            status = self.service_status()
            if not status['State']['Running']:
                break
            time.sleep(1)
        else:
            self.fail('wazo-dird did not stop while missing SSL certificate')

        log = self.service_logs()
        assert_that(
            log,
            contains_string("No such file or directory: '/tmp/ssl/dird/server.crt'"),
        )


class TestHTTPSMissingPrivateKey(DirdAssetRunningTestCase):

    asset = 'no-ssl-private-key'

    def test_given_inexisting_SSL_private_key_when_dird_starts_then_dird_stops(self):
        for _ in range(5):
            status = self.service_status()
            if not status['State']['Running']:
                break
            time.sleep(1)
        else:
            self.fail('wazo-dird did not stop while missing SSL private key')

        log = self.service_logs()
        assert_that(
            log,
            contains_string("No such file or directory: '/tmp/ssl/dird/server.key'"),
        )
