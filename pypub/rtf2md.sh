#!/usr/bin/env bash
#
#   rtf2md: convert RTF file to Markdown, using unrtf and pandoc
#
#   usage:  rtf2md <RTF input file> <Markdown output file>
#
unrtf --html $1 | \
    pandoc --normalize --smart --wrap=none -f html -t markdown | \
    # remove backslash inserted by unrtf at end of each paragraph
    sed 's/\\$/\n/g' | \
    # insert space after smushed italics '*'
    sed 's/\([\.,;:\!\?…*]\)\*\([a-zA-Z0-9“]\)/\1 \*\2/g' > $2
