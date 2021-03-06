from datetime import datetime
import json
import urllib.request

SERVER = "http://localhost:5000/add_result"

DT_FORMAT = "%Y-%m-%dT%H:%M:%S"

result_data = [
    {
        "test_name": "test name_1",
        "series_name": "posted_data",
        "batch_timestamp": datetime(2018, 1, 1).strftime(DT_FORMAT),
        "test_result": "PASS",
        "vcs_system": "git",
        "vcs_revision": "somesha1",
        "metadata": "some metadata"
    },
    {
        "test_name": "test name_1",
        "series_name": "posted_data",
        "batch_timestamp": datetime(2018, 1, 2).strftime(DT_FORMAT),
        "test_result": "PASS",
        "vcs_system": "git",
        "vcs_revision": "somesha1",
        "metadata": "some metadata"
    },
    {
        "test_name": "test name_1",
        "series_name": "posted_data",
        "batch_timestamp": datetime(2018, 1, 3).strftime(DT_FORMAT),
        "test_result": "PASS",
        "vcs_system": "git",
        "vcs_revision": "somesha1",
        "metadata": "some metadata"
    },
]

request = urllib.request.Request(SERVER)
request.add_header("Content-Type", "application/json")
print(request)
json_data = json.dumps(result_data)
print(json_data)
response = urllib.request.urlopen(request, json_data.encode("UTF-8"))
print(response)
