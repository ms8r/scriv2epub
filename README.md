# scriv2epub - utilities for creating EPUBs from Scrivener projects

## Workflow

1.  Work in EPUB top directory with Scrivener project folder as a subfolder. An exclude list can be created to prevent the subfolder to be included in the EPUB (exclude list can be passed to ``mkep`` as an argument).

2.  Create YAML file with metadata for the project (see example XXXX).

3.  Run ``ep3.py scriv2tsv`` to cerate a tsv file with each record representing a BinderItem in the Scrivener project XML file. This will also add headings and subheadings if these have been specified in the YAML metadat file. This will also generate target filenames for the individual chapters, based on their Title tags in the Scrivener project XML file.

4.  Run shell script ``scriv2md.sh`` which will convert the Scrivener RTF source files to markdown. Store markdown file in ``src`` directory. Later manual edits can be made in thes markdown files and then re-running the subsequent steps in te workflow.

5.  Run shell script ``md2htsnip.sh`` which generate clean HTML snippets (one for each chapter file in the book) from the markdown chapter files.

6.  Copy static front and backmatter HTML files (incl. any images) and stylesheet.

7.  Update the tsv file generated in step (2), adding the static front and backmatter files as well as any template-based files (e.g. title), and define sequence in which docs are to appear in EPUB.

8.  Run ``ep3.py genep`` to generate template based pages, table of contents and metadata files.

9.  Run ``mkep`` shell script to generate EPUB (and mobi is desired).

TODO:
=====

[ ] Turn paragraph formatting in md2htsnip into cl parameter
