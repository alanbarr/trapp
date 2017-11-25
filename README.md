# About

Test Result Web App is a simple database intended to store test results.

This project was little more than a learning exercise into Python, Flask and
SQLite. As such it should be considered **UNSTABLE**/**EXPERIMENTAL**.

# Environment

## First Time - Setting up the Environment

Before setting up the environment you need the following packages available in
your path:

* python3
* virtualenv
* pip

To setup the virtual environment run the following script:

    ./scripts/create_env.sh

## Activating the Environment

Run:

    source environment/bin/activate

## Exiting

To exit the virtual environment type:

    deactivate

## Running the App

### Debug

    FLASK_APP=src/run_debug.py flask run

### Gunicorn

    PYTHONPATH="$PYTHONPATH:src/" gunicorn --bind 0.0.0.0:8000 --workers 2 src.app:app


# The Nomenclature

* **Test**: Information related to a single single test. Most importantly this
    includes the name of the test and its result. 

* **Batch**: A collection of one or more tests which were run at a particular
    time. Tests in a batch should all have been run against the same target from
    the same software version.
    Note that batches within a **series** do not have to contain the same tests.

* **Series**: A collection of **batches** which have been run over time. Tests
    associated with a series should all be run against the same hardware, build
    configuration etc. 

Below is an outline of how the key components of these objects interact:

    Series n ->
               |
               |
                -> Batch n   ->
                   Timestamp   |
                   VCS Info    |
                                -> Test n
                                   Test Name
                                   Result
                                   Metadata

# State of a Test
By inspecting the history of a test in a series, the status of a test will be
identified as one of the following:

- **Passing** - the test is currently passing.
- **Newly Failing** - the test is currently failing, but has passed previously.
- **Always Failing** - the test has never passed.
- **Stale** - the test hasn't been run in a user defined time.
- **Skipped** - the test has always been skipped.

Additionally the history of a test will be scrutinised in an attempt to
determine how **stable** a test is. 
A **newly failing** test considered **stable** should be investigated before one
considered unstable.

# Submitting Result Data

## Fields

| Field             | Mandatory | Description                                       |
|-------------------|-----------|---------------------------------------------------|
|test_name          | Y         | Name of the test - should be unique               |
|series_name        | Y         | Name of the series the test result belongs to     |
|batch_timestamp    | Y         | Time the test batch run was started               |
|test_result        | Y         | Outcome of the test: "PASS", "FAIL" or "SKIP"     |
|vcs_system         | N         | Name of the version control system used           |
|vcs_revision       | N         | Revision of version control for target            |
|metadata           | N         | User defined                                      |
|test_timestamp     | N         | Time the individual test was started              |
|test_duration      | N         | Duration of the test in seconds                   |

## Timestamps

Format of timestamps is: 

    YYYY-MM-DD HH:MM:SS 
    
aka Python's:

    datetime.__str__()

or:

    datetime.isoformat(" ")


## Minimum / Mandatory Example
    [
        {
            "test_name" : "minimum example",
            "series_name" : "readme_1",
            "batch_timestamp" : "2018-01-01 20:00:00",
            "test_result" : "PASS"
        }
    ]

## Full Example

    [
        {
            "test_name" : "full example",
            "series_name" : "readme_2",
            "batch_timestamp" : "2018-01-01 20:00:00",
            "test_result" : "PASS",
            "vcs_system" : "git",
            "vcs_revision" : "6f8ccdca83b89e18f838f4702e2d4d648b1de674",
            "metadata" : "some important metadata",
            "test_timestamp" : "2018-01-01 20:20:20",
            "test_duration" : "59"
        }
    ]


# Running Tests

There is a small suite of tests which can be run by issuing:

    cd src
    python3 -m unittest -v


# Security

There is none!

