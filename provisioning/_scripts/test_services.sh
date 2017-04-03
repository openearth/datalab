#!/bin/bash
# A script to run basic tests against a host. Tests if services are up.
set -e

usage()
{
cat << EOF
usage: $0 options

This script runs basic tests against services on a machine. To parse the
vars/<hostname>.yml files; shyaml is required. Install with:
pip install shyaml

OPTIONS:
   -y  yaml file to read variables from (default: hostname.yml)
   -h  hostname of server to be tested
   -p  ssl port (default: 443)

EXAMPLE:
   ./test_services.sh -h openearth-libontw.tudelft.nl -p 443

EOF
}

# Parses vars/<host>.yml and sets username/password variables.
# user/pass are required by run test to authenticate to the server.
parse_yml()
{
    echo "Parsing vars in YAML for host $1 (vars/$1)"
    VARS_FILE="vars/$1"
    ZM_ADMIN_PASS=`cat $VARS_FILE |shyaml get-value oe_admin_pass`
}

# Run tests by calling curl or svn.
run_tests()
{
    echo "Running tests against $1:$2"
    parse_yml $3
    ADDRESS=$1:$2
    echo "Testing THREDDS"
    curl https://oe_admin:$ZM_ADMIN_PASS@$ADDRESS/thredds/catalog.html --insecure
    echo "Testing Subversion"
    svn info https://oe_admin:$ZM_ADMIN_PASS@$ADDRESS/repos/openearth
    echo "Testing LAM"
    curl https://$ADDRESS/lam/ --insecure
}

# Set options from command line
while getopts “h:p:y:” OPTION
do
     case $OPTION in
         h)
             HOST=$OPTARG
             ;;
         p)
             PORT=$OPTARG
             ;;
         y)
             YAML_FILE="$OPTARG.yml"
             ;;
         ?)
             usage
             exit
             ;;
     esac
done

# Finally run tests for host:port
if [ -z "$HOST" ] ; then
    usage
    exit
fi

# Set yaml file
if [ -z "$YAML_FILE" ] ; then
    YAML_FILE="$HOST.yml"
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

run_tests $HOST $PORT $YAML_FILE
