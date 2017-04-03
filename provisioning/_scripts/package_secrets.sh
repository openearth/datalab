#! /bin/bash
#set -e
#set -x
# These dirs contain files which should be kept secret:
INCLUDE_DIRS=(
    "files/certificates"
    "host_vars/"
)
OUTPUT="${HOME}/openearth_secrets.tar.gz"

# Make sure we're in the root of the provisioing dir.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

# Ignore files in a directory starting with a .
IGNORE_PATTERN="\/\."

# Save ignored svn files in FILES array
FILES=()
for i in "${INCLUDE_DIRS[@]}"; do
    #FILES+=( $(git ls-files --others -i --exclude-standard ../$i |grep -v -E $IGNORE_PATTERN) )
    FILES+=( $(git ls-files --others -i --exclude-standard ../$i |grep -v -E $IGNORE_PATTERN) )
done

# Add files to compressed tarball
tar -czvf $OUTPUT ${FILES[@]}
#
# Make only $USER can read it.
chmod 600 $OUTPUT
chown $USER $OUTPUT
printf "\n"
printf "Secrets stored in $OUTPUT\n"
printf "Never share these files with unsecure methods, like plaintext mail or\n"
printf "un encrypted http!\n"
