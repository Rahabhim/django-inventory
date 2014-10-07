#!/bin/bash

set -e
cd $(dirname $0)/static/js
uglifyjs --max-line-len 400 reports-app.js > reports-app.min.js

#eof
