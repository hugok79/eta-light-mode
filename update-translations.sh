#!/bin/bash

langs=("tr")
APP_NAME="eta-light-mode"

if ! command -v xgettext &> /dev/null
then
	echo "xgettext could not be found."
	echo "you can install the package with 'apt install gettext' command on debian."
	exit
fi


echo "updating pot file"
xgettext -o "po/$APP_NAME.pot" --files-from=po/files

for lang in "${langs[@]}"; do
	if [[ -f po/$lang.po ]]; then
		echo "updating $lang.po"
		msgmerge -o "po/$lang.po" "po/$lang.po" "po/$APP_NAME.pot"
	else
		echo "creating $lang.po"
		cp "po/$APP_NAME.pot" "po/$lang.po"
	fi
done
