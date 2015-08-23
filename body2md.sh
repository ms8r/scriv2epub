#!/usr/bin/env bash

#
# body2md: convert scrivener body html files to markdown
# usage: body2md <html dir> <start num> <stop num> <md prefix>
#

if [ $# != "4" ]
then
    echo
    echo ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
    echo "body2md: convert scrivener body html files to markdown"
    echo "usage: body2md <html dir> <start num> <stop num> <md prefix>"
    echo ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
    echo
    exit 1
fi

for line in $(seq $2 $3)
do
    outnum=$(( $line - $2 + 1 ))
    pandoc --no-wrap -f html -t markdown ${1}/body${line}.xhtml | \
            # delete chapter heading
            sed '/^[A-Z ]\+$/d' | \
            # insert space after smushed italics '*'
            sed 's/\([^ —]\)\*\([^ \.,;:\"\!\?]\)/\1\* \2/g' | \
            # delete empty lines at beginning
            sed '1,/[a-zA-Z]\+/ { /[a-zA-Z]\+/!d }' \
            > ${4}body${outnum}.md
done
