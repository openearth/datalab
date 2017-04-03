#!/bin/bash
# Echo's to stdout and stderr
# Uses ping -c 4 localhost for stdout to mimic running program

echo "Output for stdout 1"
echo "Output for stderr 1" >&2
ping -c 2 localhost
echo "Output for stderr 2" >&2
echo "Output for stdout 2"