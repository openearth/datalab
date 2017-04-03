#!/bin/bash
# A script to run ansible provisioning to a host. Includes git info to the files to be copied in the provisioned.

usage()
{
cat << EOF
usage: $0 [OPTIONS] -y YAML_FILE

This script provisions an OpenEarth Server with a clean git checkout. You must run this from the root of the project.

REQUIRED:
   -y  YAML_FILE  the filename of the yaml file (e.g. 'deploy_local.yml') to be used for provisioning

OPTIONS:
   -u  USERNAME   the USERNAME on the remote host
   -k  KEY_FILE   the filename of your private key used for ssh auth
   -S  SKIP_DIFF  skip the diff check with git: do not use this on accept and production environments!

EXAMPLES:
   ./provision_host.sh -y deploy_local.yml
   ./provision_host.sh -y deploy_test.yml -u remoteuser -k ~/.ssh/id_rsa

EOF
}


# check_right_dir
if [[ ! -f ./Vagrantfile ]]; then
	echo "Please run this script from the root of the project"
	exit 1
fi


# parse_args
while getopts ":y:u:k:S" opt; do
	case $opt in
		y)
			YAML=$OPTARG
			;;
		u)
			USERNAME=$OPTARG
			;;
		k)
			KEYF=$OPTARG
			;;
		S)
			SKIP_DIFF="SKIP"
			;;
		\?)
			echo "Invalid option: -$OPTARG"
			usage
			exit 1
			;;
		:)
			echo "Option -$OPTARG requires an argument."
			usage
			exit 1
			;;
	esac
done
if [ -z "$YAML" ] ; then
    echo "Option missing: -y. You must specify the yaml file to be used for ansible deployment."
    usage
    exit
fi
if [ -z "$USERNAME" ] ; then
    echo "! No USERNAME specified: using 'vagrant'"
	USERNAME="vagrant"
	ASK_SUDO_PASS=""
else
	ASK_SUDO_PASS="--ask-sudo-pass"
fi
if [ -z "$KEYF" ] ; then
    echo "! No private-keyfile specified: using /home/$(whoami)/.vagrant.d/insecure_private_key for ssh auth."
    KEYF="/home/$(whoami)/.vagrant.d/insecure_private_key"
fi


# check_git_diff
if [ -z "$SKIP_DIFF" ] ; then
	git pull
	echo "githash:unknown" > ./provisioning/roles/svn_info/files/svn_info
	GIT_DIFF=$(git diff)
	if [ ! -z "$GIT_DIFF" ] ; then
		echo ""
		echo "Provision aborted: your local files diff from git - this is not allowed! Please fix this:"
		echo ""
		echo "$GIT_DIFF"
		echo ""
		exit 1
	fi
else
	echo "!!!       You are provisioning without a diff check to git!       !!!"
	echo "!!! This is not allowed on Acceptance and Production environments !!!"
	read -p "Do you want to continue [y/N]? " -n 1 -r
	echo ""
	if [[ $REPLY =~ ^[^Yy]$ ]]; then
		exit 0
	fi
fi

# make_git_info_file
echo ""
echo "Provisioning instructions from [$YAML] are going to be run from the following GIT revision:"
git rev-parse HEAD | tee ./provisioning/roles/svn_info/files/svn_info


# provision_server
read -p "Are you sure [y/N]? " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]
then
	echo ""
	echo "$ ansible-playbook -i provisioning/hosts.cfg -vvvv --private-key=$KEYF -u $USERNAME provisioning/$YAML $ASK_SUDO_PASS"
	ansible-playbook -i provisioning/hosts.cfg -vvvv --private-key=$KEYF -u $USERNAME provisioning/$YAML $ASK_SUDO_PASS
fi
