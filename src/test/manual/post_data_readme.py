import datetime
import json
import urllib.request

SERVER = "http://localhost:5000/add_result"

result_data = [
    {
        "test_name": "minimum example",
        "series_name": "readme_1",
        "batch_timestamp": "2018-01-01T20:00:00",
        "test_result": "PASS"
    },
    {
        "test_name": "full example",
        "series_name": "readme_2",
        "batch_timestamp": "2018-01-01T20:00:00",
        "test_result": "PASS",
        "vcs_system": "git",
        "vcs_revision": "6f8ccdca83b89e18f838f4702e2d4d648b1de674",
        "metadata": "some important metadata",
        "test_timestamp": "2018-01-01 20:20:20",
        "test_duration": "59"
    }
]

request = urllib.request.Request(SERVER)
request.add_header("Content-Type", "application/json")
print(request)
json_data = json.dumps(result_data)
print(json_data)
response = urllib.request.urlopen(request, json_data.encode("UTF-8"))
print(response)
