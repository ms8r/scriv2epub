#!/usr/bin/env bash
#
#   rtf2md: convert RTF file to Markdown, using unrtf and pandoc
#
#   usage:  rtf2md <RTF inpit file> <Markdown output file>
#
unrtf --html $1 | \
    pandoc --normalize -f html -t markdown | \
    sed 's/\\$/\n/g' | \
    # insert space after smushed italics '*'
    sed 's/\([^ —]\)\*\([^ \.,;:\"\!\?]\)/\1\* \2/g' | \
    pandoc --no-wrap -f markdown -t markdown > $2
