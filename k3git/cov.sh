#!/bin/sh

set -e
coverage run --source=. -m pytest
ls -l .coverage

# coverage report

coverage html
ls -l htmlcov
open htmlcov/index.html
