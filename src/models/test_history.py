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
import models.error
from models.test_result import TestResult, SQL_TEST_QUERY
from common.database import Database
import logging
import datetime
from enum import Enum, unique

logger = logging.getLogger()

@unique
class TestState(Enum):
    passing = 0
    newly_failing = 1
    always_failing = 2
    stale = 3
    skipped = 4

# A history of the same test in the same series
class TestHistory(object):

    def __init__(self,
                 series_name,
                 test_name,
                 days_until_result_stale=0, 
                 datetime_utc_now=None):

        self.test_name = test_name
        self.series_name = series_name
        current_time = datetime.datetime.utcnow() if datetime_utc_now is None else datetime_utc_now

        if days_until_result_stale:
            self.timestamp_stale_threshold = current_time - datetime.timedelta(days=days_until_result_stale)
        else:
            self.timestamp_stale_threshold = None

        rows = Database.query_rows(
                SQL_TEST_QUERY + """
                WHERE (Test.test_name, Series.series_name) = (?,?)
                ORDER BY Batch.batch_timestamp DESC""",
                (test_name, series_name))

        self.tests = [TestResult(*r) for r in rows]

        self._determine_if_stable()
        self._get_milestones()
        self._get_state()
        self._get_last_run()

    def _get_last_run(self):
        self.last_run = self.tests[0].batch_timestamp

    # TODO - We could do with this logic.
    # For instance, if a test is passing and failing against the same VCS
    # commit.
    def _determine_if_stable(self):
        last_result = self.tests[0].test_result
        pass_count = 0;
        changes_count = 0

        non_skips = [test for test in self.tests if test.test_result != "SKIP"]

        if len(non_skips) == 0:
            self.is_stable = False
            return

        for test in non_skips:

            if test.test_result != last_result:
                changes_count += 1
                last_result = test.test_result

            if test.test_result == "PASS":
                pass_count += 1

        if pass_count / len(non_skips) <= 0.6:
            self.is_stable = False
        elif changes_count > len(non_skips) / 3:
            self.is_stable = False
        else:
            self.is_stable = True

    def _get_state(self):

        non_skipped_tests = [test for test in self.tests if test.test_result != "SKIP"]

        if len(non_skipped_tests) == 0:
            self.state = TestState.skipped
            return

        if self.timestamp_stale_threshold and \
           non_skipped_tests[0].batch_timestamp < self.timestamp_stale_threshold:
            self.state = TestState.stale
            return

        if self.last_success == non_skipped_tests[0]:
            self.state = TestState.passing
            return

        # Last non skipped test was not success. If we have a record of a
        # last_success then we have recently started to fail
        if self.last_success:
            self.state = TestState.newly_failing
            return

        # Otherwise we must have always been failing
        self.state = TestState.always_failing
    

    def _get_milestones(self):
        self.last_success = None
        self.first_fail = None
        self.is_newly_failing = False
        self.not_recently_run = False
        self.always_skipped = False

        for test in self.tests:
            if self.last_success == None:
                if test.test_result == "PASS":
                    self.last_success = test
                if test.test_result == "FAIL":
                    self.first_fail = test
        

    # TODO - potentially should remove skipped tests first, as opposed to oldest
    # first.
    # TODO - potentially could use VCS as part of batch consideration - remove
    # tests with same VCS? (Would all have to have the same result)
    def cleanup_db(self, keep_count):
        if len(self.tests) <= keep_count:
            return

        entires_to_remove = len(self.tests) - keep_count 

        logger.debug("length of tests {}".format(len(self.tests)))
        logger.debug("entries to remove {}".format(str(entires_to_remove)))

        for test in self.tests:
            logger.debug(test)

        removed_tests = []
        for test in reversed(self.tests):

            if entires_to_remove == 0:
                break

            logger.debug("Checking test {}".format(str(test)))
            logger.debug("Last success {}".format(str(self.last_success)))
            logger.debug("First fail {}".format(str(self.first_fail)))
            
            if test == self.last_success:
                continue

            if test == self.first_fail:
                logger.debug("This is first fail - skipping")
                continue

            logger.debug("Going to remove {}".format(str(test)))
            removed_tests.append(test)
            entires_to_remove -= 1
            test.db_delete()

        for removed_test in removed_tests:
            self.tests.remove(removed_test)
