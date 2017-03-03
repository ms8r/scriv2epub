#!/usr/bin/env python

"""Fixes "hanging italics" in markdown files created from Scrivener RTFs.

If a paragraph contains an uneven number of '*' (not counting '\*') an '*' will
be appended at the end and an '*' will be stripped from the start of the next
non-empty line.
"""

import re
import fileinput

def open_italics(line):
    md_stars = re.findall(r'\*', line)
    real_stars = re.findall(r'\\\*', line)
    return (len(md_stars) - len(real_stars)) % 2


orphan = False
for line in fileinput.input():
    if re.match(r'^\s*$', line):
        print(line.strip())
        continue
    if orphan:
        line = line.strip().lstrip('*')
        orphan = False
    if open_italics(line):
        print('{0}*'.format(line.strip()))
        orphan = True
    else:
        print(line.strip())

