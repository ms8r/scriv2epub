#!/usr/bin/env bash

unrtf --html $1 | pandoc --normalize -f html -t markdown | sed 's/\\$/\n/g' | pandoc --no-wrap -f markdown -t markdown > $2
