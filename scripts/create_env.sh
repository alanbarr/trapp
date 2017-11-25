#! /bin/bash
set -e

ENV_NAME=environment
PYTHON_EXE=`which python3`

virtualenv -p $PYTHON_EXE $ENV_NAME

source $ENV_NAME/bin/activate

# Make sure we have a newer version of pip installed. The version of pip which
# ships with Debian 8 will throw a SyntaxError with the async keyword when
# installing Jinja2 otherwise.
# See https://github.com/pallets/jinja/issues/643
pip install --upgrade pip

pip install --requirement requirements.txt


