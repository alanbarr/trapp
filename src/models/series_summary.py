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
from models.test_history import TestHistory, TestState
from common.database import Database
import logging
import flask_table

logger = logging.getLogger()

SQL_TEST_NAMES = """
SELECT DISTINCT 
    Test.test_name
FROM Test
    INNER JOIN Batch
        ON Test.batch_id = Batch.batch_id
    INNER JOIN Series
        ON Batch.series_id = Series.series_id
WHERE Series.series_name IS (?)
ORDER BY Test.test_name
"""

class SeriesTable(flask_table.Table):
    classes = ["table table-striped"]
    test_name = flask_table.LinkCol("Test Name",
                                    "route_view_results_series_test",
                                     url_kwargs=dict(test_name="test_name",
                                                     series_name="series_name"),
                                     attr_list="test_name")

    is_stable = flask_table.Col("Considered Stable")


class SeriesSummary(object):

    def __init__(self,series_name, days_until_result_stale=0):
        # obtain a list of all test names in this series
        # obtain a test history for each test in this series
        series_id = Database.query_one("""
            SELECT Series.series_id FROM Series 
            WHERE Series.series_name IS (?)
            """, (series_name,))
        
        tests = Database.query_rows(SQL_TEST_NAMES, (series_name,))

        self.test_histories = [TestHistory(series_name, test[0], days_until_result_stale) for test in tests]

        self.series_name = series_name

        self.newly_failing_stable_tests = [history for history in self.test_histories if history.state == TestState.newly_failing and history.is_stable == True]
        self.newly_failing_unstable_tests = [history for history in self.test_histories if history.state == TestState.newly_failing and history.is_stable == False]
        self.newly_failing_tests = self.newly_failing_stable_tests + self.newly_failing_unstable_tests
        self.always_failing_tests = [history for history in self.test_histories if history.state == TestState.always_failing]
        self.passing_tests = [history for history in self.test_histories if history.state == TestState.passing]
        self.stale_tests = [history for history in self.test_histories if history.state == TestState.stale or history.state == TestState.skipped]


    def debug(self):
        logger.debug("test histories in list: " + str(self.get_count_test_histories()))
        logger.debug("passing tests: " + str(self.get_count_passing_tests()))
        logger.debug("failing tests: " + str(self.get_count_always_failing_tests()))
        logger.debug("newly failing tests: " + str(self.get_count_newly_failing_tests()))
        logger.debug("tests not recently run: " + str(self.get_count_not_recently_run_tests()))

    def get_count_test_histories(self):
        return len(self.test_histories)

    def get_count_passing_tests(self):
        return len(self.passing_tests)

    def get_count_always_failing_tests(self):
        return len(self.always_failing_tests)

    def get_count_newly_failing_tests(self):
        return (len(self.newly_failing_stable_tests), len(self.newly_failing_tests))

    def get_count_not_recently_run_tests(self):
        return len(self.stale_tests)

    def get_always_failing_test_table(self):
        table = SeriesTable(self.always_failing_tests)
        return table.__html__()

    def get_newly_failing_test_table(self):
        table = SeriesTable(self.newly_failing_tests)
        return table.__html__()

    def get_passing_test_table(self):
        table = SeriesTable(self.passing_tests)
        return table.__html__()

    def get_stale_test_table(self):
        table = SeriesTable(self.stale_tests)
        return table.__html__()

