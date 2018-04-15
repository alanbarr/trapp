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
import models.test_result
import models.test_history
import inspect
import unittest
import os
import json

logger = logging.getLogger()

TEST_DATABASE_PATH = "test/data/test_history_stablitiy.sqlite"

DELETE_DB = True


class TestHistoryStablitiy(unittest.TestCase):

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

    def test_history_stablility(self):

        ########################################################################
        # All passing should be stable
        ########################################################################
        data = {
            "test_name": "test_name",
            "series_name": "stable_series",
            "batch_timestamp": datetime.datetime(1990, 1, 1),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        for day in range(1, 11):
            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.passing)

        self.assertEqual(hist.is_stable, True)

        ########################################################################
        # All failing should be not be stable
        ########################################################################
        data = {
            "test_name": "test_name",
            "series_name": "stable_series_but_failing",
            "batch_timestamp": datetime.datetime(1990, 1, 1),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        for day in range(1, 11):
            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.is_stable, False)
        self.assertEqual(hist.state, models.test_history.TestState.always_failing)

        ########################################################################
        # 3 Out of 10 should be unstable
        ########################################################################

        data = {
            "test_name": "test_name",
            "series_name": "unstable_series",
            "batch_timestamp": datetime.datetime(1990, 1, 1),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        for day in range(1, 11):
            if day is 2 or day is 4 or day is 6:
                data["test_result"] = "FAIL"
            else:
                data["test_result"] = "PASS"

            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            data["test_name"] = "test_unstable"
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.passing)
        self.assertEqual(hist.is_stable, False)

        ########################################################################
        # 2 Out of 10 should be stable ???
        ########################################################################
        data = {
            "test_name": "test_name",
            "series_name": "just_stable_10",
            "batch_timestamp": datetime.datetime(1990, 1, 1),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        for day in range(1, 11):
            if day is 2 or day is 10:
                data["test_result"] = "FAIL"
            else:
                data["test_result"] = "PASS"

            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            data["test_name"] = "test_unstable"
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.newly_failing)
        self.assertEqual(hist.is_stable, True)
