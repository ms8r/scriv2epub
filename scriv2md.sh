#!/usr/bin/env bash
#
# scriv2md.sh: reads tsv file produced by ep3.py scriv2tsv and converts
# Scrivener RTF files to markdown.
#


if [ $# != "2" ]
then
    echo
    echo "::::::::::::::::::::::::::::::::::::::::::::::::::::"
	echo "scriv2md: convert Scrivener rtf files to markdown"
	echo "usage: scriv2md <ep3 tsv file> <md output path>"
    echo "::::::::::::::::::::::::::::::::::::::::::::::::::::"
    echo
    exit 1
fi

# get col index for ScricSrc and ID fields in tsv file:
srccol=$(head -n 1 dummy.tsv | tr ['\t'] ['\n'] |grep -n '\<ScrivSrc\>' | cut -d: -f1)
idcol=$(head -n 1 dummy.tsv | tr ['\t'] ['\n'] |grep -n '\<ID\>' | cut -d: -f1)

for line in $(tail -n +2 $1 | grep "[1-9][0-9]*\.rtf" | \
              awk -F '\t' 'BEGIN { OFS = "|" } { print $sc, $ic }' sc=$srccol ic=$idcol)
do
    infile=${line%|*}
    outfile=$2/${line#*|}.md
    echo "converting $infile to $outfile"
    unrtf --html $infile | pandoc -f html -t markdown | sed 's/\\$/\n/g' > $outfile
done
