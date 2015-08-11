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

(x) Turn paragraph formatting in md2htsnip into cl parameter


## Background

Indie authors primarily publish eBooks
* writing for eBook more like writing for the web
    - HTML based format, multiple small files
    - Styling separate
* workflow resembles programming
    - compiled by computer program, must meet exact specifications
    - many techniques programmers have honed over time that would be useful to authors (workflow, tools, version control, collaborative development)

Issues with word processors:
* Cumbersome to work with multiple smaller files as pieces of a whole. Master Docs provide some of that functionality, but too bulky to be useful
* WYSIWYG is the wrong principle for when writing for web/EPUB. You don't control final appearance anyway but you have to make sure structure and styling is perfect. WPs are optimized for WYSIWIG presentation, very poor at extracting clean structure and styling. Inherently linked to WYSIWIG philosophy by giving user free reign over formatting features

Tools like Scrivener address some of these issues:
* Good at managing / arranging multiple file, incl. research notes, pin board
* Additional writer tools like word count targets
* Decent at producing multiple output formats for simple works (incl. EPUB)

But not sufficient for professional authors:
* RTF as underlying doc format very poor - difficult to reliably extract clean HTML
* EPUB HTML generation lacks structure (everything is <p></p>)
* CSS and HTML reflect unclean structure of underlying RTF; even Scrivener pre-defined styles are not applied / recognizable in output. Styles are simply numbered consequtively, but same style will have different names/numbers for different documents
* No support for dealing with content repeated across titles (front and back matter)
* No support for e.g. managing outgoing links, not even overview (crucial for marketing)

Lessons learned
* Use Markdown or similar (lingua franca of writing for the Web): 
    - robust conversion tools
    - light-weight (text editor)
    - results in clean HTML code
    - plain text - can use all tools incl. powerful version control and collaboration tools
* Use YAML for metadata
* If you need Scrivener or similar for writing: use it for mainmatter only, build automated workflow around it

