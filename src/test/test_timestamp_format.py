################################################################################
# Copyright (c) 2018, Alan Barr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
################################################################################
import logging
import datetime
import common.database
import models.batch
import inspect
import unittest
import os
from models.test_result import TestResult
from models.error import InvalidTimestampFormat

logger = logging.getLogger()

TEST_DATABASE_PATH = "test/data/test_timestamp_format.sqlite"

DELETE_DB = True


class TestTimestampFormat(unittest.TestCase):

    def setUp(self):
        common.database.Database.initialise(TEST_DATABASE_PATH)

    def tearDown(self):
        if DELETE_DB is False:
            return

        if os.path.isfile(TEST_DATABASE_PATH):
            logger.debug("Deleting existing test database")
            os.remove(TEST_DATABASE_PATH)

    @classmethod
    def tearDownClass(self):
        common.database.Database.shutdown()

        if DELETE_DB is False:
            return

        if os.path.isfile(TEST_DATABASE_PATH):
            logger.debug("Deleting existing test database")
            os.remove(TEST_DATABASE_PATH)

    def get_basic_result_data(self, series_name):

        data = {
            "test_name": "test name",
            "test_result": "SKIP",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        rtn = data.copy()
        rtn["series_name"] = series_name
        return rtn

    def test_with_t_seperator(self):

        current_function = inspect.stack()[0][3]
        data = self.get_basic_result_data(current_function)

        dt = datetime.datetime(2000, 10, 15)
        data["batch_timestamp"] = dt.isoformat(sep="T")

        first = TestResult(**data)
        first.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)

    def test_with_space_seperator(self):

        current_function = inspect.stack()[0][3]
        data = self.get_basic_result_data(current_function)

        dt = datetime.datetime(2001, 10, 15)
        data["batch_timestamp"] = dt.isoformat(sep=" ")

        first = TestResult(**data)
        first.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)

    def test_with_microseconds(self):

        current_function = inspect.stack()[0][3]
        data = self.get_basic_result_data(current_function)

        dt = datetime.datetime(2001, 10, 15, 12, 59, 59, 100)
        data["batch_timestamp"] = dt.isoformat(sep=" ")

        with self.assertRaises(InvalidTimestampFormat):
            first = TestResult(**data)
            first.db_save()

    def test_no_seconds(self):

        current_function = inspect.stack()[0][3]
        data = self.get_basic_result_data(current_function)

        dt = datetime.datetime(2001, 10, 15)
        datetime_format = "%Y-%m-%dT%H:%M"
        data["batch_timestamp"] = dt.strftime(datetime_format)

        with self.assertRaises(InvalidTimestampFormat):
            first = TestResult(**data)
            first.db_save()

    def test_only_date(self):

        current_function = inspect.stack()[0][3]
        data = self.get_basic_result_data(current_function)

        d = datetime.date(2001, 10, 15)
        data["batch_timestamp"] = str(d)

        with self.assertRaises(InvalidTimestampFormat):
            first = TestResult(**data)
            first.db_save()
