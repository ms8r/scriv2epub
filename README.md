# scriv2epub - utilities for streamlining EPUB creation from Scrivener projects

[Scrivener](http://www.literatureandlatte.com/scrivener.php) is a desktop
application used by many indie fiction authors as their bread-and-butter tool
for creating content. While Scrivener offers good support for the writing
process, it is mediocre at best at generating professional eBook output (EPUB
and its Amazon MOBI sibling), the main format for most indie authors.
_scriv2epub_  is a set of simple command line utilities that seek to address
this shortcoming, allowing authors to use Scrivener for what it's good at
(generating and organizing content) but take the pain out of all the manual
fixes required to turn Scrivener generated eBooks into consistently
high-quality products. Specifically, _scriv2epub_ generates clean HTML out of
Scrivener's RTF source files and uses a templating system linked to a central
stylesheet to generate the HTML and XML outputs required for EPUBs. It uses a
YAML config file to store book metadata and structure info. It also allows
reuse of content across different books. This works e.g. for front and
backmatter material but also to bundle existing books into box sets.


## Key components of _scriv2epub_

* __s2e.py__: the Python 3 script that runs the whole thing from the command
  line. It provides the following commands (run ``python s2e.py <command> -h``
  for info about options):

    - ``init`` to initialize a new EPUB project
    - ``scrivx2yaml`` to extract the relevant mainmatter structure information
      from the Scrivener project file (usually ``project.scrivx`` in the
      Scrivener project root directory).
    - ``scriv2md`` to convert the Scrivener RTF source files to
      Markdown,preserving italics but scrubbing all other format info (using
      [unrtf](https://www.gnu.org/software/unrtf/unrtf.html) and
      [pandoc](http://pandoc.org/))
    - ``genep`` to generate to full EPUB content and metadata
    - ``genlatex`` to generate LaTeX for a print book, given a YAML metadata
      file, mainmatter (as a single markdown file), and a jinja template (see
      ``tex_book`` templates in ``tmpl`` directory.
    - ``mmcat`` to concatenate all mainmatter markdown sources with headings
      inserted at the correct levels (the output can be used for the
      ``genlatex`` command).

* [__Jinja2__](http://jinja.pocoo.org) __templates__ (in directory ``tmpl``):
  the basis for HTML content and XML metadata files, as well as for LaTeX
  output. These templates reference ``stylesheet.css`` for styling/formatting
  (see tree structure below).

* __meta.yaml__ (in directory ``epub``): this file contains the metadata for
  the EPUB as well as the specification for front and backmatter content, and
  overall book structure. See below for details on the structure of this file.

Additional supporting bits and pieces:

* __rtf2md.sh__: bash script for RTF to Markdown conversion.

* __md2htsnip__: bash script for converting Markdown files to HTML snippets
  (body content only, called by s2e.py via ``subprocess.Popen()``). In addition
  to the conversion via _pandoc_ it also adds a basic CSS styling (using styles
  defined in ``epub/OPS/css/stylsheet.css``in ``epub/OPS/css/stylsheet.css``)
* __num2eng.py__: module adapted from [Miki Tebeka's
  blog](http://www.blog.pythonlibrary.org/2012/06/02/how-to-convert-decimal-numbers-to-words-with-python/)
  to spell out numerals in English (used for automatic chapter heading
  numbering).
* __Makefile__: canbe used to streamline workflow iterating through updates and
  corrections. Defined targets are ``content`` (generates fresh HTML/XML EPUB
  files from Markdown and YAML sources), ``epub`` (to generate EPUB eBook), and
  `` mobi`` (to generate Amazon MOBI eBook; requires
  [KindleGen](http://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000765211))
  and [EpubCheck](https://github.com/idpf/epubcheck).  See comments in
  ``Makefile`` for more info.


## Workflow with Scrivener and _scriv2epub_:

1.  Create your mainmatter content in Scrivener.

2.  Run ``python s2e.py init`` to initialize a new EPUB directory tree,
    pre-populated with a CSS stylesheet and the boilerplate EPUB files such as
    ``mimetype`` and ``container.xml`` (run with ``-h`` argument to see more
    options). ``init`` will also initialize a blank git repository under the
    newly created ``epub`` directory and provide a standard ``.gitignore``
    file. In addition, it will provide a default ``exclude.list`` file that can
    be used during the EPUB zipping to prevent supporting files and directories
    to be included into the EPUB zip file.

3.  Update the ``meta.yaml`` template that is provided as part of the ``init``
    setup in the EPUB root directory. Enter EPUB metadata, and the required
    front and backmatter data. See comments in ``meta.yaml`` for available page
    templates and how content elements for these can be specified.

4.  Run ``python s2e.py scrivx2yaml`` to extract required mainmatter data
    (incl. paths to RTF source files) from the Scrivener project file and
    append output to ``meta.yaml``. Run with ``-h`` argument to see more
    options.

5.  Run ``python s2e.py scriv2md`` to convert Scrivener RTF files to Markdown.
    Depending on your preferences you can make future content edits directly in
    these Markdown files or continue to work in Scrivener and re-run
    ``scriv2md`` after edits.

Once you're done with (5) you will have your book content in clean Markdown
formatted files (one file per chapter or whatever the split in Scrivener was)
in the ``src`` directory.  If you use these as your master copy, you will only
have to re-run steps (6) and (7) below whenever you make updates to the content
(which is quick and easy if you use the supplied ``Makefile``).

To actually generate your eBook do the following:

6.  Run ``python s2e.py genep`` (or run ``make content``) to generate the full
    EPUB content (run with ``-h`` argument to see options). This will generate
    the EPUB metadata files (content.opf, toc.ncx), the HTML table of contents,
    all front and backmatter pages specified in the ``meta.yaml`` file, and of
    course the mainmatter content.

7.  Finally, you will need to zip these files into an EPUB, run your preferred
    EPUB checker, and convert to MOBI if required. Alternatively you can run
    ``make epub`` (zips required files into epub and runs EpubCheck) and ``make
    mobi`` (makes an Amazon mobi file out of the EPUB version).

A powerful feature of _scriv2epub_ is the ability to reuse content across
different books. For example, you can maintain a central repository of front
and backmatter elements (as Markdown or HTML files) such as "About the author",
"Other books by the author", etc. You can then simply reference these in each
book's ``meta.yaml`` file so they will be automatically included in the
resulting eBook. In combination with the templates you can even do some
book-specific customization for these common content elements. Whenver you
update one of the central files (e.g. by adding a new title to your book list)
you simply re-run steps (6) and (7) above to update your eBooks with the new
content.

The same mechanism can be used to assemble existing content into an omnibus or
to combine muliple titles into a boxed set, without having to duplicate the
underlying content files. Similarly, to provide a sneak preview to another
title at the end of a book you can simply reference the corresponding Markdown
source file in the ``meta.yaml`` file. ``meta.yaml`` also allows you to aplly
some "customization" to these referenced files such as adding a preamble or a
post script.

Last but not least _scriv2epub_ also provides a basic mechanism to add Google
Analytics UTM parameters to URLs in a book's front and backmatter. These allow
you to track which link was clicked where in what book. See the comments in
``meta.yaml`` for details


## Directory structure created by ``init``

    epub/
       |
       |-- mimetype             boilerplate EPUB
       |
       |-- meta.yaml            metadata info, and front and backmater specs
       |
       |-- exclude.list         list of directories and files to excluded from
       |                        EPUB zipping (argument to zip's -x option)
       |
       |-- META-INF/
       |          |
       |          --- container.xml     EPUB boilerplate
       |
       |-- OPS/                 all generated content (XHTML) and EPUB metadata
       |     |                  will be placed in this directory
       |     |
       |     |-- css/
       |     |     |
       |     |     --- stylesheet.css
       |     |
       |     --- img/           place cover.jpg and all other required image
       |                        files in this directory (will be picked up
       |                        automatically for OPF manifest)
       |
       --- src/                 place Markdown files generated from Scrivener
             |                  RFT files in this directory; also any static
             |                  XHTML files which are to be copied into EPUB
             |
             --- cover.xhtml

This tree is created by simply copying the ``epub`` subtree from the directory
this README file resides in. If you have additional files to be included in the
default setup just add them to the epub subtree.


## Structure of ``meta.yaml`` file

See the comments in the boilerplate ``meta.yaml`` file for details. The basic
structure is:

1. EPUB metadata such as title, author, description, keywords. These will be
   used to populate Title and Copyright page templates as well as the EPUB
   metadata XML files.

2. The book contents, broken down in frontmatter, mainmatter, and backmatter.
   The mainmatter section can be generated automatically from the Scrivener
   ``project.scrivx`` file via s2e's ``scrivx2yaml`` command. For each section
   the YAML file contains a list of pages to be created for this section. Each
   list item specifies

    - an *id* that will be used for the XHTML filename and as identifier in
      EPUB metadate files.
    - a *heading* that will be used to populate the jinja template. Optionally
      also a subheading can be specified.
    - a *type*. This determines how the corresponding XHTML page will be
      generated. Options are 'static' (existing \<id\>.XHTML will be copied
      from ``src`` directory), 'template' (jinja template to be populated with
      combination of metadata and page data specified in the YAML file), and
      'chapter' (mainmatter content that will be generated from Markdown source
      files). See comments in YAML boilerplate for details on 'template' type
      and additional optional page parameters.

For front and/or backmatter pages of type 'template' an additional top-level
section in the YAML file can be provided (keyed with the page id) to define the
detailed content for the page. For example, for book listings, the individual
titles and URLs to be listed can be specified in this way. This detailed
content definition for a page can also be broken out in a separate YAML file
named ``<page id>.yaml`` and -if desired- kept in a central `include` directory
that can used across books.

In general, any items in the YAML file(s) that are used to replace variables in
the jinja templates must be keyed by the respective variable names in the
template(s).

See the README file in the `tmpl` directory for a short description of each available template.

