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
import models.error as error
import logging
from common.database import Database
import json
import datetime

logger = logging.getLogger()

TEST_RESULTS = ["PASS", "FAIL", "SKIP"]
TIMESTAMP_FORMAT = "%Y-%m-%d{}%H:%M:%S"

SQL_TEST_QUERY = """
SELECT
        Test.test_name,
        Series.series_name,
        Batch.batch_timestamp,
        Test.test_result,
        Vcs.vcs_system,
        Vcs.vcs_revision,
        Metadata.metadata,
        Test.test_timestamp,
        Test.test_duration,
        Test.test_id,
        Batch.batch_id,
        Series.series_id,
        Metadata.metadata_id,
        Vcs.vcs_id
FROM Test
    INNER JOIN Batch
        ON Test.batch_id = Batch.batch_id
    INNER JOIN Series
        ON Batch.series_id = Series.series_id
    LEFT JOIN Vcs
        ON Batch.vcs_id = Vcs.vcs_id
    LEFT JOIN Metadata
        ON Test.metadata_id = Metadata.metadata_id
"""


# A single test
class TestResult(object):

    def __init__(self,
                 test_name,
                 series_name,
                 batch_timestamp,
                 test_result,
                 vcs_system=None,
                 vcs_revision=None,
                 metadata=None,
                 test_timestamp=None,
                 test_duration=None,
                 test_id=None,
                 batch_id=None,
                 series_id=None,
                 metadata_id=None,
                 vcs_id=None
                 ):

        if test_result not in TEST_RESULTS:
            raise error.InvalidArgument(
                    "Result was {}".format(test_result))

        self.series_name = series_name

        if type(batch_timestamp) == str:
            batch_timestamp = self._string_to_datetime(batch_timestamp)
        self.batch_timestamp = batch_timestamp

        self.vcs_system = vcs_system
        self.vcs_revision = vcs_revision
        self.metadata = metadata
        self.test_name = test_name
        self.test_result = test_result

        if type(test_timestamp) == str:
            test_timestamp = self._string_to_datetime(test_timestamp)
        self.test_timestamp = test_timestamp

        self.test_duration = test_duration

        self.series_id = series_id
        self._db_series_get_id()

        self.batch_id = batch_id
        self._db_batch_get_id()

        self.vcs_id = vcs_id
        self._db_vcs_get_id()

        self.metadata_id = metadata_id
        self._db_metadata_get_id()

        self.test_id = test_id
        self._db_test_get_id()

        logger.debug("Created a TestResult object: {}".format(test_name))

    def __repr__(self):
        return "<{} {:#08x} - test_id: {} name: {} series_name: {} " \
               "timestamp: \"{}\" test_result: {}>".format(
                    self.__class__.__name__,
                    id(self),
                    self.test_id,
                    self.test_name,
                    self.series_name,
                    self.batch_timestamp.strftime(TIMESTAMP_FORMAT.format("T")),
                    self.test_result)

    def __eq__(self, other):

        if other is None:
            return False

        if self.__dict__ != other.__dict__:
            return False

        assert self.__dict__["batch_timestamp"] == other.__dict__["batch_timestamp"]

        return True

    def _db_test_save(self):

        if self.test_id is not None:
            return

        self.test_id = Database.execute(
                            """INSERT INTO Test
                                (test_name,
                                 test_result,
                                 test_timestamp,
                                 test_duration,
                                 batch_id,
                                 metadata_id)
                                 VALUES (?,?,?,?,?,?)""",
                            (self.test_name,
                             self.test_result,
                             self.test_timestamp,
                             self.test_duration,
                             self.batch_id,
                             self.metadata_id, ))

    def _db_test_get_id(self):

        if self.test_id is not None:
            return

        if self.batch_id is None:
            return

        self.test_id = Database.query_one(
                            """SELECT test_id FROM Test WHERE
                            (test_name = ? AND  batch_id = ?)""",
                            (self.test_name, self.batch_id))

    def _db_vcs_save(self):

        if self.vcs_id is not None:
            return
        if self.vcs_system is None:
            return

        self.vcs_id = Database.execute(
                            """INSERT INTO Vcs
                            (vcs_system, vcs_revision) VALUES (?,?)""",
                            (self.vcs_system, self.vcs_revision))

    def _db_vcs_get_id(self):

        if self.vcs_id is not None:
            return

        if self.vcs_system is None or self.vcs_revision is None:
            return

        self.vcs_id = Database.query_one(
                            """SELECT vcs_id FROM Vcs WHERE
                            (vcs_system = ? AND vcs_revision = ?)""",
                            (self.vcs_system, self.vcs_revision))

    def _db_metadata_save(self):

        if self.metadata_id is not None:
            return
        if self.metadata is None:
            return

        self.metadata_id = Database.execute(
                            """INSERT INTO Metadata (metadata) VALUES (?)""",
                            (self.metadata, ))

    def _db_metadata_get_id(self):

        if self.metadata_id is not None:
            return

        if self.metadata is None:
            return

        self.metadata_id = Database.query_one(
                            """SELECT metadata_id FROM Metadata WHERE
                            metadata = (?)""",
                            (self.metadata,))

    def _db_series_save(self):

        if self.series_id is not None:
            return

        self.series_id = Database.execute(
                            """INSERT INTO Series (series_name) VALUES (?)""",
                            (self.series_name,))

    def _db_series_get_id(self):

        if self.series_id is not None:
            return

        self.series_id = Database.query_one(
                    """SELECT series_id FROM Series WHERE series_name = (?)""",
                    (self.series_name,))

    def _db_batch_save(self):

        if self.batch_id is not None:
            return

        self.batch_id = Database.execute(
                            """INSERT INTO Batch
                            (series_id, batch_timestamp, vcs_id)
                            VALUES (?,?,?)""",
                            (self.series_id, self.batch_timestamp, self.vcs_id))

    def _db_batch_get_id(self):

        if self.batch_id is not None:
            return

        if self.series_id is None:
            return

        self.batch_id = Database.query_one(
                            """SELECT batch_id FROM Batch WHERE
                            (batch_timestamp = ? AND series_id = ?)""",
                            (self.batch_timestamp, self.series_id))

    def db_save(self):
        self._db_vcs_save()
        self._db_metadata_save()
        self._db_series_save()
        self._db_batch_save()
        self._db_test_save()

    def db_delete(self):
        Database.execute("""DELETE FROM Test WHERE Test.test_id = (?)""",
                         (self.test_id, ))
        self.test_id = None

        if Database.query_one(
                """SELECT COUNT () FROM Test WHERE Test.batch_id = (?)""",
                (self.batch_id,)) == 0:

            Database.execute("""DELETE FROM Batch WHERE Batch.batch_id = (?)""",
                             (self.batch_id, ))
        self.batch_id = None

        if Database.query_one(
                """SELECT COUNT () FROM Batch WHERE Batch.series_id = (?)""",
                (self.series_id,)) == 0:

            Database.execute("""DELETE FROM Series WHERE Series.series_id = (?)""",
                             (self.series_id, ))

        self.series_id = None

        if Database.query_one(
                """SELECT COUNT () FROM Test WHERE Test.metadata_id = (?)""",
                (self.metadata_id,)) == 0:

            Database.execute(
                    """DELETE FROM Metadata WHERE Metadata.metadata_id = (?)""",
                    (self.metadata_id, ))

        self.metadata_id = None

        if Database.query_one(
                """SELECT COUNT () FROM Batch WHERE Batch.vcs_id = (?)""",
                (self.vcs_id,)) == 0:

            Database.execute("""DELETE FROM Vcs WHERE Vcs.vcs_id = (?)""",
                             (self.vcs_id, ))
        self.vcs_id = None

    @classmethod
    def get_by_id(cls, test_id):
        logger.debug("Finding by id")
        row = Database.query_row(
            SQL_TEST_QUERY + """WHERE test_id = (?) """, (test_id,))
        return cls(*row)

#    @classmethod
#    def save_json_results(cls, json_data):
#
#        if isinstance(json, str):
#            py_data = json.loads(json_data)
#        else:
#            py_data = json_data
#
#        if isinstance(py_data, dict):
#            py_data = [py_data]
#
#        Database.start_batch()
#
#        for entry in py_data:
#            result = cls(**entry)
#            result.db_save()
#
#        Database.end_batch()

    def compare_values(self,
                       test_name,
                       series_name,
                       batch_timestamp,
                       test_result,
                       vcs_system=None,
                       vcs_revision=None,
                       metadata=None,
                       test_timestamp=None,
                       test_duration=None):

        if self.test_name != test_name:
            logger.debug("Not equal: test_name")
            return False

        if self.series_name != series_name:
            logger.debug("Not equal: series_name")
            return False

        if type(batch_timestamp) == str:
            batch_timestamp = self._string_to_datetime(batch_timestamp)

        if self.batch_timestamp != batch_timestamp:
            logger.debug("Not equal: batch_timestamp <{}> <{}>".format(
                                                    str(self.batch_timestamp),
                                                    str(batch_timestamp)))
            return False

        if self.test_result != test_result:
            logger.debug("Not equal: test_result")
            return False

        if self.vcs_system != vcs_system:
            logger.debug("Not equal: vcs_system")
            return False

        if self.vcs_revision != vcs_revision:
            logger.debug("Not equal: vcs_revision")
            return False

        if self.metadata != metadata:
            logger.debug("Not equal: metadata")
            return False

        if self.test_timestamp != test_timestamp:
            logger.debug("Not equal: test_timestamp")
            return False

        if self.test_duration != test_duration:
            logger.debug("Not equal: test_duration")
            return False

        return True

    @staticmethod
    def _string_to_datetime(timestamp):
        if "T" in timestamp:
            datetime_format = TIMESTAMP_FORMAT.format("T")
        else:
            datetime_format = TIMESTAMP_FORMAT.format(" ")

        try:
            dt = datetime.datetime.strptime(timestamp, datetime_format)
        except ValueError as err:
            raise error.InvalidTimestampFormat(
                    "Invalid timestamp string {}".format(timestamp)) from err

        return dt
