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
import uuid
import sqlite3
import logging
import os

SCHEMA = """
CREATE TABLE IF NOT EXISTS Vcs (
    vcs_id          INTEGER PRIMARY KEY, 
    vcs_system      TEXT NOT NULL,
    vcs_revision    TEXT NOT NULL,

    CONSTRAINT revision_unique UNIQUE (vcs_system, vcs_revision)
);

CREATE TABLE IF NOT EXISTS Series (
    series_id       INTEGER PRIMARY KEY NOT NULL, 
    series_name     TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS Metadata (
    metadata_id     INTEGER PRIMARY KEY NOT NULL,
    metadata        TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS Batch ( 
    batch_id        INTEGER PRIMARY KEY, 
    batch_timestamp TIMESTAMP NOT NULL,
    series_id       INTEGER NOT NULL,
    vcs_id          INTEGER,

    FOREIGN KEY(vcs_id) REFERENCES Vcs_System(vcs_id),
    FOREIGN KEY(series_id) REFERENCES Series(series_id),
    CONSTRAINT batch_in_series_unique UNIQUE (batch_timestamp, series_id)
);

CREATE TABLE IF NOT EXISTS Test (
    test_id         INTEGER PRIMARY KEY,
    test_name       TEXT NOT NULL,
    test_result     TEXT NOT NULL,
    test_timestamp  TIMESTAMP,
    test_duration   INTEGER,
    batch_id        INTEGER NOT NULL,
    metadata_id     INTEGER,

    FOREIGN KEY(metadata_id) REFERENCES Metadata(metadata_id),
    FOREIGN KEY(batch_id) REFERENCES Batch(batch_id),
    CONSTRAINT test_in_batch_unique UNIQUE (test_name, batch_id)
);
"""


logger = logging.getLogger()


class DatabaseDebug(object):
    def __init__(self, **kwds):
        self.__dict__ = kwds

class Database(object):

    _conn = None
    _is_batch = False

    def __init__(self):
        raise Exception("{} is a singleton".format(self.__class__.__name__))

    @classmethod
    def initialise(cls, database_file):

        directory = os.path.dirname(database_file)
        if not os.path.exists(directory):
            logger.debug("Creating database path: {}".format(directory));
            os.makedirs(directory)

        cls._conn = sqlite3.connect(database = database_file,
                                    detect_types = sqlite3.PARSE_DECLTYPES)

        cur = cls._conn.cursor()
        cur.executescript(SCHEMA)

        logger.info("Opened database: {}".format(database_file))

    @classmethod
    def shutdown(cls):
        cls._conn.close()

    @classmethod
    def query_one(cls, command, args=()):
        cur = cls._conn.cursor()
        cur.execute(command, args)
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]

    @classmethod
    def query_row(cls, command, args=()):
        cur = cls._conn.cursor()
        cur.execute(command, args)
        result = cur.fetchone()
        return result

    @classmethod
    def query_rows(cls, command, args=()):
        cur = cls._conn.cursor()
        cur.execute(command, args)
        result = cur.fetchall()
        return result


    @classmethod
    def execute(cls, command, args=()):
        cur = cls._conn.cursor()
        cur.execute(command, args)

        if cls._is_batch == False:
            cls._conn.commit()

        return cur.lastrowid

    @classmethod
    def _get_entry_count(cls, table):
        return cls.query_one("""SELECT COUNT () FROM {} """.format(table))

    @classmethod
    def get_debug(cls):
        return DatabaseDebug(countTest=cls._get_entry_count("Test"),
                             countBatch=cls._get_entry_count("Batch"),
                             countSeries=cls._get_entry_count("Series"),
                             countVcs=cls._get_entry_count("Vcs"),
                             countMetadata=cls._get_entry_count("Metadata"))

    @classmethod
    def start_batch(cls):
        cls._is_batch = True

    @classmethod
    def end_batch(cls):
        cls._conn.commit()
        cls._is_batch = False



