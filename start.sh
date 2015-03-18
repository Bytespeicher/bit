#!/bin/sh

WWW_ROOT=$(dirname $0)

if [ -z "$1" ]
then
	echo "$0: Missing argument start|stop"
	exit 255
fi

if [ "$1" == "start" ]
then
	spawn-fcgi -d "$WWW_ROOT" -f "$WWW_ROOT/bit.py" -a 127.0.0.1 -p 9002
elif [ "$1" == "stop" ]
then
	kill `pgrep -f "python $WWW_ROOT/bit.py"`
else
	echo "Unknown command $2"
	exit 3
fi
