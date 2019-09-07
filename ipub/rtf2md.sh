#!/usr/bin/env bash
#
#   rtf2md: convert RTF file to Markdown, using libreoffice and pandoc
#
#   usage:  rtf2md <RTF input file> <Markdown output file>
#

set -e

SCRIPTFILE=$(basename $0)

if [ $# != "2" ]
then
	echo "${SCRIPTFILE}: convert doc/odt/rtf to markdown"
	echo "usage: ${SCRIPTFILE} <input file> <markdown output file>"
	exit 1
fi

TMPDIR=$(mktemp -d .${SCRIPTFILE%.*}.XXXXXXXX)

libreoffice --convert-to html --outdir $TMPDIR $1 2> /dev/null
INFILE=$(basename $1)

sed -e 's:</\?span[^>]*>::g' \
    -e 's:</\?font[^>]*>::g' \
    -e 's:<p [^>]*>:<p>:g' < $TMPDIR/${INFILE%.*}.html | \
    pandoc --normalize --smart --wrap=none -f html -t markdown | \
    sed '/^\\[ ]*$/d' > $2

rm $TMPDIR/${INFILE%.*}.html
rmdir $TMPDIR
