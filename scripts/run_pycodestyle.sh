#! /bin/bash

# TODO - get this down to something more respectable
LINE_LENGTH=180

pycodestyle --max-line-length=${LINE_LENGTH} src/
