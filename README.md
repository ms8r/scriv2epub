# scriv2epub - utilities for streamlining EPUB creation from Scrivener projects

[Scrivener](http://www.literatureandlatte.com/scrivener.php) is a desktop application used by many indie fiction authors as their bread-and-butter tool for creating content. While Scrivener offers good support for the writing process, it is mediocre at best at generating professional eBook output (EPUB and its Amazon MOBI sibling), the main format for most indie authors. _scriv2epub_  is a set of simple command line utilities that seek to address this shortcoming, allowing authors to use Scrivener for what it's good at (generating and organizing content) but take the pain out of all the manual fixes required to turn Scrivener generated eBooks into consistently high-quality products. Specifically, _sriv2epub_ generates clean HTML out of Scrivener's RTF source files and uses a templating system linked to a central stylesheet to generate the HTML and XML outputs required for EPUBs. It uses a YAML formatted to store book metadata and structure and allows to automate generation of content that is used across different book titles.


## Key components of _scriv2epub_

* __s2e.py__: the Python 3 script that runs the whole thing from the command line. It provides the following commands (run ``python s2e.py <command> -h`` for info about options):

    - ``init`` to initialize a new EPUB project
    - ``scrivx2yaml`` to extract the relevant mainmatter structure information from the Scrivener project file (usually ``project.scrivx`` in the Scrivener project root directory).
    - ``scriv2md`` to convert the Scrivener RTF source files to Markdown,preserving italics but scrubbing all other format info (using [unrtf](https://www.gnu.org/software/unrtf/unrtf.html) and [pandoc](http://pandoc.org/))
    - ``genep`` to generate to full EPUB content and metadata

* [__Jinja2__](http://jinja.pocoo.org) __templates__: the basis for HTML content and XML metadata files. These reference ``stylesheet.css`` for styling/formatting (see tree structure below).

* __meta.yaml__: this files contains the metadata for the EPUB as well as the specification for front and backmatter content, and overall book structure. See below for details on the structure of this file.

Additional supporting bits and pieces:

* __rtf2md.sh__: bash script for RTF to Markdown conversion (called by s2e.py via ``subprocess.Popen()``).

* __md2htsnip__: bash script for converting Markdown files to HTML snippets (body content only, called by s2e.py via ``subprocess.Popen()``). In addition to the conversion via _pandoc_ it also adds a basic CSS class for all mainmatter paragraphs and centers paragraphs that match "\<\<\<[ ]\*\>\>\>".

* __num2eng.py__: module adapted from [Miki Tebeka's blog](http://www.blog.pythonlibrary.org/2012/06/02/how-to-convert-decimal-numbers-to-words-with-python/) to spell out numerals in English (used for automatic chapter heading numbering).


## Workflow with Scrivener and _scriv2epub_:

1.  Create your mainmatter content in Scrivener.

2.  Run ``python s2e.py init`` to initialize a new EPUB directory tree, pre-populated with a CSS stylesheet and the boilerplate EPUB files such as ``mimetype`` and ``container.xml`` (run with ``-h`` argument to see more options). ``init`` will also initialize a blank git repository under the newly created ``epub`` directory and provide a standard ``.gitignore`` file. In addition, it will provide a default ``exclude.list`` file taht cab be used during the EPUB zipping to prevent supporting files and directories to be included into the EPUB zip file.

3.  Update the ``meta.yaml`` template that is provided as part of the ``init`` setup in the EPUB root directory. Enter EPUB metadata, and the required front and backmatter data. See comments in ``meta.yaml`` for available page templates and how content elements for these can be specified.

4.  Run ``python s2e.py scrivx2yaml`` to extract required mainmatter data (incl. paths to RTF source files) from the Scrivener project file and append output to ``meta.yaml``. Run with ``-h`` argument to see more options.

5.  Run ``python s2e.py scriv2md`` to convert Scrivener RTF files to Markdown. Depending on your preferences you can make future content edits directly in these Markdown files or continue to work in Scrivener and re-run ``scriv2md`` after edits.

6.  Run ``python s2e.py genep`` to generate the full EPUB content (run with ``-h`` argument to see options). This will generate the EPUB metadata files (content.opf, toc.ncx), the HTML table of contents, all front and backmatter pages specified in the ``meta.yaml`` file, and of course the mainmatter content.

7.  Finally, you will need to zip these files into an EPUB, run your preferred EPUB checker, and convert to MOBI if required.


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

This tree is created by simply copying the ``epub`` subtree from the directory this README file resides in. If you have additional files to be included in the default setup just add them to the epub subtree.


## Structure of ``meta.yaml`` file

See the comments in the boilerplate ``meta.yaml`` file for details. The basic structure is:

1. EPUB metadata such as title, author, description, keywords. These will be used to populate Title and Copyright page templates as well as the EPUB metadata XML files.

2. The book contents, broken down on frontmatter, mainmatter, and backmatter. The mainmatter section can be generated automatically from the Scrivener ``project.scrivx`` file via s2e's ``scrivx2yaml`` command. For each section the YAML file contains a list of pages to be created for this section. Each list item specifies

    - an *id* that will be used for the XHTML filename and as identifier in EPUB metadate files.
    - a *heading* that will be used to populate the jinja template. Optionally also a subheading can be specified.
    - a *type*. This determines how the corresponding XHTML page will be generated. Options are 'static' (existing \<id\>.XHTML will be copied from ``src`` directory), 'template' (jinja template to be populated with combination of metadata and page data specified in the YAML file), and 'chapter' (mainmatter content that will be generated from Markdown source files). See comments in YAML boilerplate for details on 'template' type and additional optional page parameters.

For front and/or backmatter pages of type 'template' an additional top-level section in the YAML file can be provided (keyed with the page id) to define the detailed content for the page. For example, for book listings, the individual titles and URLs to be listed can be specified in this way. This detailed content definition for a page can also be broken out in a separate YAML file named ``<page id>.yaml``.

In general, any items in the YAML file(s) that are used to replace variables in the jinja templates must be keyed by the respective variable names in the template(s).


## Available templates

* __opf.jinja__: basis for content.opf EPUB metadata file

* __ncx.jinja__: basis for toc.ncx EPUB navigation map

* __xhtml_skeleton.jinja__: base template that is extended by the templates listed subsequently which overwrite the ``body`` block

* __title.jinja__: title page template

* __copyright.jinja__: copyright page

* __chapter.jinja__: mainmatter chapter; default style is ``par-indent``, can be changed for a specific page to another style available in ``OPS/css/stylesheet.css`` by providing a ``parstyle`` parameter for the respective page in ``meta.yaml``

* __book_list.jinja__: basis for book listings by series, with or without images; see comment in template for details

* __noindent_pars.jinja__: simple template with heading, subheading and unindented, parskipped paragraphs; text content can be specified in ``meta.yaml``


