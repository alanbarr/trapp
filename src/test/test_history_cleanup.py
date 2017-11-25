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
logging.basicConfig()
logger.setLevel(logging.DEBUG)

TEST_DATABASE_PATH = "test/data/test_history_cleanup.sqlite"
DELETE_DB = True

class TestCleanup(unittest.TestCase):

    def setUp(self):
        common.database.Database.initialise(TEST_DATABASE_PATH)

    def tearDown(self):
        if DELETE_DB is False:
            return

        if os.path.isfile(TEST_DATABASE_PATH):
            logger.debug("Deleting existing test database")
            os.remove(TEST_DATABASE_PATH)

    @classmethod
    def tearDownClass(cls):
        common.database.Database.shutdown()

        if DELETE_DB is False:
            return

        if os.path.isfile(TEST_DATABASE_PATH):
            logger.debug("Deleting existing test database")
            os.remove(TEST_DATABASE_PATH)

    def test_remove_extra_passes(self):
        entries_to_add = 11

        template = {
            "test_name" : "test name",
            "series_name" : "posted_data",
            "test_result" : "PASS",
            "vcs_system" : "git",
            "vcs_revision" : "somesha1",
            "metadata" : "some metadata"
        }

        initial_test_data = []
        for i in range(1, entries_to_add + 1):
            temp = dict(template)
            temp["batch_timestamp"] = str(datetime.datetime(2018,1,i))
            initial_test_data.append(temp)

        json_data = json.dumps(initial_test_data)

        models.batch.add_batch(json_data, 0)

        # History Should contain 11 tests
        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), entries_to_add)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        # Request cleanup of length 10 - last entry should be removed
        target_length = 10

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = reversed(initial_test_data)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

        # Request cleanup of length 2 - last entries should be removed
        target_length = 2
        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = reversed(initial_test_data)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))


        # TODO XXX what happens to reference to deleted object? Do we set
        # everything to None?

    def test_single_pass_at_end(self):
        entries_to_add = 11

        template = {
            "test_name" : "test name",
            "series_name" : "posted_data",
            "test_result" : "FAIL",
            "vcs_system" : "git",
            "vcs_revision" : "somesha1",
            "metadata" : "some metadata"
        }

        initial_test_data = []

        temp = dict(template)
        temp["batch_timestamp"] = str(datetime.datetime(2018,1,1))
        temp["test_result"] = "PASS"
        initial_test_data.append(temp)

        for i in range(2, entries_to_add + 1):
            temp = dict(template)
            temp["batch_timestamp"] = str(datetime.datetime(2018,1,i))
            initial_test_data.append(temp)

        json_data = json.dumps(initial_test_data)

        models.batch.add_batch(json_data, 0)

        # History Should contain 11 tests
        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), entries_to_add)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        # Request cleanup to remove just one entry - last FAIL entry (first in
        # time) should be kept, as should the only PASS. Second fail by batch
        # time should be removed
        target_length = entries_to_add - 1

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        initial_test_data.remove(initial_test_data[2])
        newest_first = reversed(initial_test_data)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

        # Request cleanup of length 2 - first FAIL and single PASS should
        # remain

        target_length = 2

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = iter([initial_test_data[1], initial_test_data[0]])

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

    def test_always_failing_keep_first_fail(self):
        entries_to_add = 11

        template = {
            "test_name" : "test name",
            "series_name" : "posted_data",
            "test_result" : "FAIL",
        }

        initial_test_data = []
        for i in range(1, entries_to_add + 1):
            temp = dict(template)
            temp["batch_timestamp"] = str(datetime.datetime(2000,1,i))
            initial_test_data.append(temp)

        json_data = json.dumps(initial_test_data)

        models.batch.add_batch(json_data, 0)

        # History Should contain 11 tests
        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), entries_to_add)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        # Request cleanup of length 10 - second last entry should be removed
        target_length = 10

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = initial_test_data
        newest_first.remove(newest_first[1])
        newest_first = reversed(initial_test_data)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

        # Request cleanup of length 2 - should have first and last
        target_length = 2
        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = iter([initial_test_data[-1], initial_test_data[0]])

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))


    # 20 tests, first test and last test are passes
    # Keep 9 tests.
    # Oldest 11 tests should be deleted - 1 pass and 8 skips remain
    def test_passes_and_skips_last_skip(self):
        entries_to_add = 20

        template = {
            "test_name" : "test name",
            "series_name" : "posted_data",
            "test_result" : "SKIP"
        }

        initial_test_data = []
        for i in range(1, entries_to_add + 1):
            temp = dict(template)
            temp["batch_timestamp"] = str(datetime.datetime(2000,1,i))
            initial_test_data.append(temp)

        initial_test_data[0]["test_result"] = "PASS"
        initial_test_data[-1]["test_result"] = "PASS"

        json_data = json.dumps(initial_test_data)

        models.batch.add_batch(json_data, 0)

        # History should contain 20 tests
        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), entries_to_add)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        # Request cleanup - check remaining tests
        target_length = 9

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = initial_test_data[-target_length : ]
        logger.error("len(newest_first): " + str(len(newest_first)))
        self.assertTrue(len(newest_first) == len(retrieved.tests))
        newest_first = reversed(initial_test_data)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

    # 20 tests, first test and last test are skips, rest pass
    # Keep 5 tests.
    # Oldest 15 tests should be deleted - 1 skip and 4 pass remain
    def test_passes_and_skips_last_skip(self):
        entries_to_add = 20

        template = {
            "test_name" : "test name",
            "series_name" : "posted_data",
            "test_result" : "PASS"
        }

        initial_test_data = []
        for i in range(1, entries_to_add + 1):
            temp = dict(template)
            temp["batch_timestamp"] = str(datetime.datetime(2000,1,i))
            initial_test_data.append(temp)

        initial_test_data[0]["test_result"] = "SKIP"
        initial_test_data[-1]["test_result"] = "SKIP"

        json_data = json.dumps(initial_test_data)

        models.batch.add_batch(json_data, 0)

        # History should contain all
        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), entries_to_add)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        # Request cleanup - check remaining tests
        target_length = 5

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = initial_test_data[-target_length : ]
        self.assertTrue(len(newest_first) == len(retrieved.tests))
        newest_first = reversed(initial_test_data)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))
            

    # 10 tests oldest is pass, then fail. Newest 8 skip
    # Keep 5 tests:
    #   Expect 3 skips, fail, pass
    # Keep 2 tests:
    #   Expect fail, pass
    def test_recent_all_skips(self):
        entries_to_add = 10

        template = {
            "test_name" : "test name",
            "series_name" : "posted_data",
            "test_result" : "SKIP"
        }

        initial_test_data = []
        for i in range(1, entries_to_add + 1):
            temp = dict(template)
            temp["batch_timestamp"] = str(datetime.datetime(2000,1,i))
            initial_test_data.append(temp)

        initial_test_data[0]["test_result"] = "PASS"
        initial_test_data[1]["test_result"] = "FAIL"

        json_data = json.dumps(initial_test_data)

        models.batch.add_batch(json_data, 0)

        # History should contain all the tests.
        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), entries_to_add)
        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        # Request cleanup - check remaining tests
        target_length = 5

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = initial_test_data[-1:-4:-1]
        newest_first.append(initial_test_data[1])
        newest_first.append(initial_test_data[0])
        self.assertEqual(len(newest_first), len(retrieved.tests))
        newest_first = iter(newest_first)

        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

        # Request cleanup - only fail and pass should remain
        target_length = 2

        retrieved.cleanup_db(target_length)

        retrieved = models.test_history.TestHistory(template["series_name"],
                                                    template["test_name"])

        self.assertEqual(len(retrieved.tests), target_length)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, target_length)

        newest_first = []
        newest_first.append(initial_test_data[1])
        newest_first.append(initial_test_data[0])
        self.assertEqual(len(newest_first), len(retrieved.tests))
        newest_first = iter(newest_first)


        for i in range(target_length):
            self.assertTrue(retrieved.tests[i].compare_values(**next(newest_first)))

