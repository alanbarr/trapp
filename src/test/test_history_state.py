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
import models.batch
from models.test_history import TestHistory, TestState
import inspect
import unittest
import os
import json

logger = logging.getLogger()

TEST_DATABASE_PATH = "test/data/test_history_state.sqlite"

DELETE_DB = True

datetime.datetime.utcnow()


class TestHistoryState(unittest.TestCase):

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

    def test_stale(self):

        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2018, 3, 14)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2018, 3, 14)),
            "test_duration": 60
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        ########################################################################
        # Limit set to 0, test is not state
        ########################################################################
        fake_todays_date = datetime.datetime(2018, 3, 18)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Limit set to non-zero but so that test is not stale
        ########################################################################
        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=4,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Set now before test timestamp - test should be marked stale
        ########################################################################
        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=3,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.stale)

        ########################################################################
        # Add a new test dated within the valid range - no longer stale.
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2018, 3, 15)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 3, 15)),
            "test_duration": 60
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=4,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Further restrict stale threshold - test is stale
        ########################################################################
        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=2,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.stale)

    def test_stale_skipped_is_ignored(self):

        fake_todays_date = datetime.datetime(2018, 5, 10)

        ########################################################################
        # Add passing test with next day - test is passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2018, 5, 7)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=3,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add skipped test with next day. Increase threshold by a day.
        # Test should not be considered by logic and history now seen as stale
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2018, 5, 8)),
            "test_result": "SKIP",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=2,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.stale)

        ########################################################################
        # Add next day passing test - state is passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2018, 5, 9)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=1,
                                datetime_utc_now=fake_todays_date)

        self.assertEqual(len(retrieved.tests), 3)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 3)
        self.assertEqual(retrieved.state, TestState.passing)

    def test_passing(self):
        ########################################################################
        # Add passing test - passing
        ########################################################################

        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 10)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 10)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add passing test with next day - test is passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 11)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 11)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.passing)

    def test_newly_failing(self):
        ########################################################################
        # Add passing test - passing
        ########################################################################

        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 10)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 10)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add passing test with next day - test is passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 11)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 11)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add failing test - newly_failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 12)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 12)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 3)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 3)
        self.assertEqual(retrieved.state, TestState.newly_failing)

        ########################################################################
        # Add passing test - passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 13)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 13)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 4)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 4)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add failing test - newly failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 14)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 14)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 5)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 5)
        self.assertEqual(retrieved.state, TestState.newly_failing)

        ########################################################################
        # Add skipped test - newly failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2010, 10, 15)),
            "test_result": "SKIP",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2010, 10, 15)),
            "test_duration": 1
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 6)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 6)
        self.assertEqual(retrieved.state, TestState.newly_failing)

    def test_always_failing(self):

        ########################################################################
        # Add failing test - always failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 1)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 1)),
            "test_duration": 2
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.always_failing)

        ########################################################################
        # Add failing test - always failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 2)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 2)),
            "test_duration": 2
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.always_failing)

        ########################################################################
        # Add failing test - always failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 3)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 3)),
            "test_duration": 2
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 3)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 3)
        self.assertEqual(retrieved.state, TestState.always_failing)

        ########################################################################
        # Add skipped test - always failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 4)),
            "test_result": "SKIP",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 4)),
            "test_duration": 10
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 4)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 4)
        self.assertEqual(retrieved.state, TestState.always_failing)

        ########################################################################
        # Add passing test - passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 5)),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 5)),
            "test_duration": 10
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 5)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 5)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add failing test - newly_failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 6)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 6)),
            "test_duration": 10
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 6)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 6)
        self.assertEqual(retrieved.state, TestState.newly_failing)

        ########################################################################
        # Add failing test - newly_failing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2009, 1, 7)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata",
            "test_timestamp": str(datetime.datetime(2009, 1, 7)),
            "test_duration": 10
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 7)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 7)
        self.assertEqual(retrieved.state, TestState.newly_failing)

    def test_skipped(self):

        ########################################################################
        # Add skipped test - skipped
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2000, 12, 1)),
            "test_result": "SKIP",
            "vcs_system": "fossil",
            "vcs_revision": "something",
            "metadata": "skipped this test for reason x",
            "test_timestamp": str(datetime.datetime(2000, 12, 1)),
            "test_duration": 2
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 1)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(retrieved.state, TestState.skipped)

        ########################################################################
        # Add skipped test - skipped
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2000, 12, 2)),
            "test_result": "SKIP",
            "vcs_system": "fossil",
            "vcs_revision": "something",
            "metadata": "skipped this test for reason y",
            "test_timestamp": str(datetime.datetime(2000, 12, 2)),
            "test_duration": 5
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 2)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(retrieved.state, TestState.skipped)

        ########################################################################
        # Add passing test - passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2000, 12, 3)),
            "test_result": "PASS",
            "vcs_system": "fossil",
            "vcs_revision": "something 5",
            "metadata": "finally fan the test",
            "test_timestamp": str(datetime.datetime(2000, 12, 3)),
            "test_duration": 5
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 3)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 3)
        self.assertEqual(retrieved.state, TestState.passing)

        ########################################################################
        # Add skipped test - passing
        ########################################################################
        test_result_data = {
            "test_name": "test name",
            "series_name": "posted_data",
            "batch_timestamp": str(datetime.datetime(2000, 12, 4)),
            "test_result": "SKIP",
            "vcs_system": "fossil",
            "vcs_revision": "something",
            "metadata": "skipped this test for reason z",
            "test_timestamp": str(datetime.datetime(2000, 12, 4)),
            "test_duration": 5
        }

        json_data = json.dumps(test_result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = TestHistory(test_result_data["series_name"],
                                test_result_data["test_name"],
                                days_until_result_stale=0)

        self.assertEqual(len(retrieved.tests), 4)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 4)
        self.assertEqual(retrieved.state, TestState.passing)
