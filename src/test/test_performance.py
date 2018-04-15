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
import time
import common.database
import models.test_result
import models.batch
import models.test_history
import inspect
import unittest
import os
import json

logger = logging.getLogger()
logging.basicConfig()
logger.setLevel(logging.INFO)


TEST_DATABASE_PATH = "test/data/test_performance.sqlite"

DELETE_DB = True

class TestPerformance(unittest.TestCase):

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

    def test_all_fields(self):

        entries_to_add = 10000

        result_data = []
        for i in range(entries_to_add):
            temp = dict()
            temp["series_name"] = "all fields {}".format(i)
            temp["test_result"] = "PASS"
            temp["vcs_system"] = "git"
            temp["metadata"] ="metadata: {}".format(i)
            temp["test_name"] = "test name {}".format(i)
            temp["batch_timestamp"] = str(datetime.datetime.fromtimestamp(i))
            temp["test_timestamp"] = str(datetime.datetime.fromtimestamp(i))
            temp["vcs_revision"] = i
            temp["test_duration"] = i
            result_data.append(temp)

        json_data = json.dumps(result_data)

        time_before = time.time()
        models.batch.add_batch(json_data, 0)
        time_delta = time.time() - time_before

        logger.info("Adding {} entries took {} seconds".format(entries_to_add,
                                                               time_delta))

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        db_size = os.path.getsize(TEST_DATABASE_PATH)
        logger.info("Database size: {}".format(db_size))


    def test_only_mandatory_fields(self):

        entries_to_add = 10000

        result_data = []
        for i in range(entries_to_add):
            temp = dict()
            temp["series_name"] = "mandatory fields {}".format(i)
            temp["test_name"] = "test name {}".format(i)
            temp["test_result"] = "PASS"
            temp["batch_timestamp"] = str(datetime.datetime.fromtimestamp(i))
            result_data.append(temp)

        json_data = json.dumps(result_data)

        time_before = time.time()
        models.batch.add_batch(json_data, 0)
        time_delta = time.time() - time_before

        logger.info("Adding {} entries took {} seconds".format(entries_to_add,
                                                               time_delta))

        db_dbg = common.database.Database.get_debug()
        self.assertEqual(db_dbg.countTest, entries_to_add)

        db_size = os.path.getsize(TEST_DATABASE_PATH)
        logger.info("Database size: {}".format(db_size))


