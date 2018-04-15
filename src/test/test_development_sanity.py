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
import models.batch
import inspect
import unittest
import os
import json

logger = logging.getLogger()

TEST_DATABASE_PATH = "test/data/test_dev_sanity.sqlite"

DELETE_DB = True


class TestDevelopment(unittest.TestCase):

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

    def test_create_duplicates(self):
        current_function = inspect.stack()[0][3]

        data = {
            "test_name": "test name",
            "series_name": current_function,
            "batch_timestamp": datetime.datetime(2017, 12, 12),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        first = models.test_result.TestResult(**data)
        first.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)

        duplicate = models.test_result.TestResult(**data)
        duplicate.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)

        self.assertEqual(first, duplicate)

        retrieved = models.test_result.TestResult.get_by_id(first.test_id)

        self.assertEqual(first, retrieved)

    def test_object_compare(self):

        current_function = inspect.stack()[0][3]

        data = {
            "test_name": "test name",
            "series_name": current_function,
            "batch_timestamp": datetime.datetime(2015, 10, 15),
            "test_result": "SKIP",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        first = models.test_result.TestResult(**data)
        first.db_save()

        duplicate = models.test_result.TestResult(**data)
        duplicate.db_save()

        self.assertEqual(first, duplicate)

        # test_name
        duplicate.test_name = "a test"
        self.assertNotEqual(first, duplicate)

        duplicate.test_name = data["test_name"]
        self.assertEqual(first, duplicate)

        # series_name
        duplicate.series_name = "unexpected series"
        self.assertNotEqual(first, duplicate)

        duplicate.series_name = data["series_name"]
        self.assertEqual(first, duplicate)

        # batch_timestamp
        duplicate.batch_timestamp = datetime.datetime(2020, 2, 2)
        self.assertNotEqual(first, duplicate)

        duplicate.batch_timestamp = data["batch_timestamp"]
        self.assertEqual(first, duplicate)

        # test_result
        duplicate.test_result = "PASS"
        self.assertNotEqual(first, duplicate)

        duplicate.test_result = data["test_result"]
        self.assertEqual(first, duplicate)

        # vcs_system
        duplicate.vcs_system = "fossil"
        self.assertNotEqual(first, duplicate)

        duplicate.vcs_system = data["vcs_system"]
        self.assertEqual(first, duplicate)

        # vcs_revision
        duplicate.vcs_revision = "1"
        self.assertNotEqual(first, duplicate)

        duplicate.vcs_revision = data["vcs_revision"]
        self.assertEqual(first, duplicate)

        # metadata
        duplicate.metadata = "1"
        self.assertNotEqual(first, duplicate)

        duplicate.metadata = data["metadata"]
        self.assertEqual(first, duplicate)

    def test_create_two_in_batch(self):
        current_function = inspect.stack()[0][3]

        data = {
            "test_name": "test name_1",
            "series_name": current_function,
            "batch_timestamp": datetime.datetime(2017, 12, 12),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        first = models.test_result.TestResult(**data)
        first.db_save()

        data["test_name"] = "test_name_2"
        data["test_result"] = "FAIL"

        second = models.test_result.TestResult(**data)
        second.db_save()

        retrieved_first = models.test_result.TestResult.get_by_id(first.test_id)
        self.assertEqual(first, retrieved_first)

        retrieved_second = models.test_result.TestResult.get_by_id(second.test_id)
        self.assertEqual(second, retrieved_second)

    def test_history_passing(self):
        data = {
            "test_name": "test_name",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        ########################################################################
        # Most recent test failing
        ########################################################################
        data["series_name"] = "most recent failing"
        data["test_result"] = "PASS"

        for day in range(1, 11):
            if day is 10:
                data["test_result"] = "FAIL"

            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.newly_failing)

        ########################################################################
        # Most recent test passing
        ########################################################################
        data["series_name"] = "most recent passing"
        data["test_result"] = "FAIL"

        for day in range(1, 11):
            if day is 10:
                data["test_result"] = "PASS"

            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.passing)

        ########################################################################
        # Most recent test skip, failing
        ########################################################################
        data["series_name"] = "most recent skip, fail"
        data["test_result"] = "PASS"

        for day in range(1, 11):
            if day is 10:
                data["test_result"] = "SKIP"
            elif day is 9:
                data["test_result"] = "FAIL"

            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.newly_failing)

        ########################################################################
        # Most recent test skip, passing
        ########################################################################
        data["series_name"] = "most recent skip, pass"
        data["test_result"] = "FAIL"

        for day in range(1, 11):
            if day is 10:
                data["test_result"] = "SKIP"
            elif day is 9:
                data["test_result"] = "PASS"

            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.is_newly_failing, False)
        self.assertEqual(hist.state, models.test_history.TestState.passing)

        ########################################################################
        # All skip
        ########################################################################
        data["series_name"] = "all skipped"
        data["test_result"] = "SKIP"

        for day in range(1, 11):
            data["batch_timestamp"] = datetime.datetime(1990, 1, day)
            test = models.test_result.TestResult(**data)
            test.db_save()

        hist = models.test_history.TestHistory(data["series_name"],
                                               data["test_name"])

        self.assertEqual(hist.state, models.test_history.TestState.skipped)

    def test_json_list(self):

        result_data = [
            {
                "test_name": "test name_1",
                "series_name": "posted_data",
                "batch_timestamp": str(datetime.datetime(2018, 1, 1)),
                "test_result": "PASS",
                "vcs_system": "git",
                "vcs_revision": "somesha1",
                "metadata": "some metadata"
            },
            {
                "test_name": "test name_1",
                "series_name": "posted_data",
                "batch_timestamp": str(datetime.datetime(2018, 1, 2)),
                "test_result": "PASS",
                "vcs_system": "git",
                "vcs_revision": "somesha1",
                "metadata": "some metadata"
            },
            {
                "test_name": "test name_1",
                "series_name": "posted_data",
                "batch_timestamp": str(datetime.datetime(2018, 1, 3)),
                "test_result": "PASS",
                "vcs_system": "git",
                "vcs_revision": "somesha1",
                "metadata": "some metadata"
            },
        ]

        json_data = json.dumps(result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = models.test_history.TestHistory(result_data[0]["series_name"],
                                                    result_data[0]["test_name"])

        self.assertEqual(len(retrieved.tests), 3)
        self.assertEqual(retrieved.state, models.test_history.TestState.passing)

    def test_json_not_list(self):

        result_data = {
            "test_name": "test name_1_json",
            "series_name": "json_not_list",
            "batch_timestamp": str(datetime.datetime(1990, 1, 1)),
            "test_result": "FAIL",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        json_data = json.dumps(result_data)

        models.batch.add_batch(json_data, 0)

        retrieved = models.test_history.TestHistory(result_data["series_name"],
                                                    result_data["test_name"])

        self.assertEqual(retrieved.state, models.test_history.TestState.always_failing)
        self.assertEqual(len(retrieved.tests), 1)

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(db_dbg.countBatch, 1)
        self.assertEqual(db_dbg.countSeries, 1)
        self.assertEqual(db_dbg.countMetadata, 1)
        self.assertEqual(db_dbg.countVcs, 1)

    def test_delete_one(self):
        ########################################################################
        # Add one entry delete it
        ########################################################################

        data = {
            "test_name": "deleting_this",
            "series_name": "single_delete",
            "batch_timestamp": datetime.datetime(2018, 1, 1),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1",
            "metadata": "some metadata"
        }

        first = models.test_result.TestResult(**data)
        first.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(db_dbg.countBatch, 1)
        self.assertEqual(db_dbg.countSeries, 1)
        self.assertEqual(db_dbg.countVcs, 1)
        self.assertEqual(db_dbg.countMetadata, 1)

        first.db_delete()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 0)
        self.assertEqual(db_dbg.countBatch, 0)
        self.assertEqual(db_dbg.countSeries, 0)
        self.assertEqual(db_dbg.countVcs, 0)
        self.assertEqual(db_dbg.countMetadata, 0)

    def test_delete_two_independant(self):
        ########################################################################
        # Add two entries, all different. delete one, delete other
        ########################################################################
        data_1 = {
            "test_name": "deleting_this_1",
            "series_name": "double_delete_1",
            "batch_timestamp": datetime.datetime(2018, 1, 1),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1_1",
            "metadata": "some metadata_1"
        }
        data_2 = {
            "test_name": "deleting_this_2",
            "series_name": "double_delete_2",
            "batch_timestamp": datetime.datetime(2018, 1, 2),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1_2",
            "metadata": "some metadata_2"
        }

        first = models.test_result.TestResult(**data_1)
        first.db_save()

        second = models.test_result.TestResult(**data_2)
        second.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(db_dbg.countBatch, 2)
        self.assertEqual(db_dbg.countSeries, 2)
        self.assertEqual(db_dbg.countVcs, 2)
        self.assertEqual(db_dbg.countMetadata, 2)

        first.db_delete()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(db_dbg.countBatch, 1)
        self.assertEqual(db_dbg.countSeries, 1)
        self.assertEqual(db_dbg.countVcs, 1)
        self.assertEqual(db_dbg.countMetadata, 1)

        retrieved_scond = models.test_result.TestResult.get_by_id(second.test_id)
        self.assertEqual(second, retrieved_scond)

        second.db_delete()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 0)
        self.assertEqual(db_dbg.countBatch, 0)
        self.assertEqual(db_dbg.countSeries, 0)
        self.assertEqual(db_dbg.countVcs, 0)
        self.assertEqual(db_dbg.countMetadata, 0)

    def test_delete_two_shared(self):
        ########################################################################
        # Add two entries, shared config. delete one. shared data should persist
        ########################################################################
        data_1 = {
            "test_name": "deleting_this_1",
            "series_name": "double_delete_1",
            "batch_timestamp": datetime.datetime(2018, 1, 1),
            "test_result": "PASS",
            "vcs_system": "git",
            "vcs_revision": "somesha1_1",
            "metadata": "some metadata_1"
        }

        data_2 = dict(data_1)
        data_2["test_name"] = "deleting_this_2"

        first = models.test_result.TestResult(**data_1)
        first.db_save()

        second = models.test_result.TestResult(**data_2)
        second.db_save()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 2)
        self.assertEqual(db_dbg.countBatch, 1)
        self.assertEqual(db_dbg.countSeries, 1)
        self.assertEqual(db_dbg.countVcs, 1)
        self.assertEqual(db_dbg.countMetadata, 1)

        first.db_delete()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 1)
        self.assertEqual(db_dbg.countBatch, 1)
        self.assertEqual(db_dbg.countSeries, 1)
        self.assertEqual(db_dbg.countVcs, 1)
        self.assertEqual(db_dbg.countMetadata, 1)

        retrieved_scond = models.test_result.TestResult.get_by_id(second.test_id)
        self.assertEqual(second, retrieved_scond)

        second.db_delete()

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, 0)
        self.assertEqual(db_dbg.countBatch, 0)
        self.assertEqual(db_dbg.countSeries, 0)
        self.assertEqual(db_dbg.countVcs, 0)
        self.assertEqual(db_dbg.countMetadata, 0)

    def test_no_optional_data(self):
        data_1 = {
            "test_name": "deleting_this_1",
            "series_name": "double_delete_1",
            "batch_timestamp": datetime.datetime(2018, 1, 1),
            "test_result": "PASS",
        }

        first = models.test_result.TestResult(**data_1)
        first.db_save()

        retrieved = models.test_history.TestHistory(data_1["series_name"],
                                                    data_1["test_name"])

        self.assertEqual(len(retrieved.tests), 1)
