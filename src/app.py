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
import os
import logging
import logging.handlers
from models.test_result import TestResult
from models.test_history import TestHistory
from models.series_summary import SeriesSummary
from models.series_names import SeriesNames
from models.batch import add_batch
from common.database import Database
import flask_table 
from flask import Flask, render_template, url_for, request

logger = logging.getLogger()

class FormattedTable(flask_table.Table):
    classes = ["table table-striped"]

def create_logger(level, log_file=None, log_to_stdout=False):

    fmt_str = "%(asctime)s - %(levelname)s - %(filename)s - %(message)s"

    formatter = logging.Formatter(fmt_str)

    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        logger.debug("Creating path for logs: {}".format(log_dir));
        os.makedirs(log_dir)

    if log_file:
        log_file_size_bytes = 2 * 1024**2
        fh = logging.handlers.RotatingFileHandler(log_file,
                                                  maxBytes=log_file_size_bytes,
                                                  backupCount=3)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    if log_to_stdout:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    logger.setLevel(level)


################################################################################

app = Flask(__name__)

app.config.from_object("config")

create_logger(app.config["LOG_LEVEL"], app.config["LOG_FILE"])

@app.before_first_request
def db_initalise():
    Database.initialise(app.config["DATABASE"])

@app.route("/debug")
def route_debug():
    return "debug"

@app.route("/echo:<string>")
def route_echo(string):
    return render_template("echo.jinja2", echo_string=string)

@app.route("/")
@app.route("/results")
def route_view_results():

    all_series = SeriesNames.get_all()
    all_series = [dict(series_name=x[0]) for x in all_series]

    class SeriesTable(FormattedTable):
        series_name = flask_table.LinkCol("Series",
                                          "route_view_results_series_landing",
                                          url_kwargs=dict(series_name="series_name"),
                                          attr_list="series_name")
    table = SeriesTable(all_series)

    return render_template("series_selection.jinja2", series_list=table.__html__())


# TODO can the below two methods be tidied up / combined?
@app.route("/results/series/<path:series_name>/type/<result_type>")
def route_view_results_series_for_type(series_name, result_type):

    series = SeriesSummary(series_name,
                           app.config["DAYS_UNTIL_TEST_RESULT_STALE"])

    types = {
        "newly_failing" : ("Newly Failing Tests",
                           series.get_newly_failing_test_table()),
        "passing"  : ("Currently Passing Tests",
                      series.get_passing_test_table()),
        "always_failing" : ("Always Failing Tests",
                     series.get_always_failing_test_table()),
        "stale" : ("State Tests / Tests Not Recently Run",
                    series.get_stale_test_table())
    }

    title, table = types[result_type]

    return render_template("results_for_series_single.jinja2",
                           series_name=series_name,
                           title=title,
                           table=table)

@app.route("/results/series/<path:series_name>")
def route_view_results_series_landing(series_name):

    series = SeriesSummary(series_name,
                           app.config["DAYS_UNTIL_TEST_RESULT_STALE"])

    newly_failing_url = url_for(endpoint="route_view_results_series_for_type",
                                series_name=series_name,
                                result_type="newly_failing")

    passing_url = url_for(endpoint="route_view_results_series_for_type",
                          series_name=series_name,
                          result_type="passing")

    always_failing_url = url_for(endpoint="route_view_results_series_for_type",
                          series_name=series_name,
                          result_type="always_failing")

    stale_url = url_for(endpoint="route_view_results_series_for_type",
                        series_name=series_name,
                        result_type="stale")

    (newly_failing_stable_count, newly_failing_total_count) = series.get_count_newly_failing_tests()

    return render_template("results_for_series_links.jinja2",
                           series_name=series_name,
                           total_tests=series.get_count_test_histories(),
                           newly_failing_url=newly_failing_url,
                           newly_failing_stable_count = newly_failing_stable_count,
                           newly_failing_total_count = newly_failing_total_count,
                           passing_url=passing_url,
                           passing_count=series.get_count_passing_tests(),
                           always_failing_url=always_failing_url,
                           always_failing_count=series.get_count_always_failing_tests(),
                           stale_url=stale_url,
                           stale_count=series.get_count_not_recently_run_tests())

@app.route("/results/series/<path:series_name>/test/<path:test_name>")
def route_view_results_series_test(series_name, test_name):

    history = TestHistory(series_name, test_name)

    class ItemTable(FormattedTable):
        test_result = flask_table.Col("Result")
        batch_timestamp = flask_table.Col("Batch Timestamp")
        vcs_system = flask_table.Col("VCS")
        vcs_revision = flask_table.Col("VCS Revision")
        test_timestamp = flask_table.Col("Test Timestamp")
        metadata = flask_table.Col("Metadata")

    table = ItemTable(history.tests)

    return render_template("results_for_single_test_in_series.jinja2",
                            series_name=series_name, 
                            test_name=test_name, 
                            is_stable=history.is_stable,
                            history_table=table.__html__())

@app.route("/add_result", methods=["POST"])
def route_add_result():

    py_data = request.get_json()

    add_batch(py_data,app.config["TEST_HISTORY_SIZE"])

    return "OK"

def create_table(series_name):
    
    x = TestHistory(series_name, "test_name")

    class ItemTable(FormattedTable):
        test_name = flask_table.Col("Test Name")
        series_name = flask_table.Col("Series Name")
        batch_timestamp = flask_table.Col("timestamp")

    table = ItemTable(x.tests)

    return table.__html__()
