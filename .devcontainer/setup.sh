#!/bin/bash

python setup.py develop
pip install -e .[test]
pip install black
