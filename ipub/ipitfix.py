#!/usr/bin/env python

"""Fixes "hanging italics" in markdown files created from Scdrivener RTFs.

If a paragraph contains an uneven number of '*' (not counting '\*') an '*' will
be appended at the end and an '*' will be stripped from the start of the next
non-empty line. Also corrects italics formatting strtching over multiple
paragraphs.
"""

import re
import fileinput

def ast_count(line):
    return len(re.findall(r'\*', line))

def esc_ast_count(line):
    return len(re.findall(r'\\\*', line))

def it_ast_count(line):
    return ast_count(line) - esc_ast_count(line)

def open_italics(line):
    return (it_ast_count(line) % 2) != 0

with fileinput.input() as input_:
    orphan = False
    for line in input_:
        if open_italics(line):
            line = '{0}*\n'.format(line.rstrip())
            orphan = True
            while orphan:
                nl = next(input_)
                if re.match(r'^\s*$', nl):
                    line += nl
                    continue
                if open_italics(nl):
                    if nl.strip().startswith('*'):
                        line += nl.replace('*', '', 1)
                    else:
                        line += '*{0}'.format(nl)
                    orphan = False
                else:
                    line += '*{0}*\n'.format(nl.rstrip())
        print(line.rstrip())

