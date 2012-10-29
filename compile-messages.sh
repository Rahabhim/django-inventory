#!/bin/bash

cd $(dirname "$0")
BASEDIR=$(pwd)
for APP in apps/* ; do
        pushd $APP || continue 
        $BASEDIR/manage.py compilemessages -l el
        popd 
done

#eof


