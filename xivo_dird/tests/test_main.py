# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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

from mock import Mock
from mock import patch
from unittest import TestCase
from xivo_dird import main


class TestMain(TestCase):

    def setUp(self):
        main.daemonize = Mock()

    @patch('xivo_dird.dird_server.DirdServer', Mock(return_value=Mock()))
    def test_that_main_inititlize_the_logger(self):
        main._init_logger = Mock()

        main.main()

        main._init_logger.assert_called_once_with()

    def test_that_main_runs_the_server(self):
        with patch('xivo_dird.dird_server.DirdServer') as MockDirdServer:
            instance = MockDirdServer.return_value

            main.main()

            instance.run.assert_called_once_with()

    @patch('xivo_dird.dird_server.DirdServer', Mock(return_value=Mock()))
    def test_that_dird_is_daemonized(self):
        main.main()

        main.daemonize.daemonize.assert_called_once_with()

    @patch('xivo_dird.dird_server.DirdServer', Mock(return_value=Mock()))
    def test_that_dird_has_a_pid_file(self):
        main.main()

        main.daemonize.lock_pidfile_or_die.assert_called_once_with(main._PID_FILENAME)
        main.daemonize.unlock_pidfile.assert_called_once_with(main._PID_FILENAME)

    def test_that_the_pid_file_is_unlocked_on_exception(self):
        with patch('xivo_dird.dird_server.DirdServer',
                   Mock(return_value=Mock(run=Mock(side_effect=AssertionError('Unexpected'))))):

            main.main()

            main.daemonize.lock_pidfile_or_die.assert_called_once_with(main._PID_FILENAME)
            main.daemonize.unlock_pidfile.assert_called_once_with(main._PID_FILENAME)


@patch('logging.getLogger')
class TestInitLogger(TestCase):

    def test_that_init_logger_sets_the_level_to_debug(self, get_logger_mock):
        logger = Mock()
        get_logger_mock.return_value = logger

        main._init_logger()

        logger.setLevel.assert_called_once_with(logging.DEBUG)

    @patch('logging.StreamHandler')
    def test_that_a_stream_handler_is_set(self, stream_handler_mock, get_logger_mock):
        handler = Mock()
        logger = Mock()
        get_logger_mock.return_value = logger
        stream_handler_mock.return_value = handler

        main._init_logger()

        logger.addHandler.assert_called_once_with(handler)
