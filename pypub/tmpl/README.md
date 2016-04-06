## Available templates

### General EPUB:

* __opf.jinja__: basis for content.opf EPUB metadata file

* __ncx.jinja__: basis for toc.ncx EPUB navigation map

* __xhtml_skeleton.jinja__: base template that is extended by the templates
  listed subsequently which overwrite the ``body`` block

* __title.jinja__: title page template

* __copyright.jinja__: copyright page

* __toc.jinja__: table of contents, supporting nested chapter hierarchy if
  defined in meta.yaml and mainmatter.yaml via `children` attribute

* __nav_toc.jinja__: table of contents that includes HTML5 `nav` tags to define
  logical table of contents and landmarks ("cover", "toc", "bodymatter").
  Double functions as HTML toc and logical toc that can replace NCX toc. Newer
  Amazon devices are using the `nav` information in this file rather than NCX
  data to build logical table of contents.

* __chapter.jinja__: mainmatter chapter; default style is ``par-indent``, can
  be changed for a specific page to another style available in
  ``OPS/css/stylesheet.css`` by providing a ``parstyle`` parameter for the
  respective page in ``meta.yaml``

* __book_list.jinja__: basis for book listings by series, with or without
  images; see comment in template for details

* __noindent_pars.jinja__: simple template with heading, subheading and
  unindented, parskipped paragraphs; text content can be specified in
  ``meta.yaml``

* __recommended_reads.jinja__: Defines the structure for "Recommended Reads"
  references to other author's books. Can have multiple sections, each with its
  own heading

### For box sets:

* __blurb_list.jinja__: defines the structure for listing an overview of books
  (e.g. in a box set) with a title (optionally linked and with suffix),
  subtitle, and a list of paragraphs.for each book.

* __part_title.jinja__: page to start new book in a box set with title and
  optionally subtitle, plain sub text, series, and author, as well as an image

### For print books (via pdflatex):

These tenmplates produce LaTeX output and use a different set of delimiters to
avoid interfering with LaTeX' {} (see comments in template).

* __tex_book_5.25x8.jinja__: template for LaTeX CreateSpace print book 5.25" x
  8" using *memoir* document class. Will ``\inlcude`` mainmatter content which
  needs to available as a separate LaTeX file (file name passed in as
  ``mainmatter`` argument)

* __tex_book_5.06x7.81.jinja__: same as previous but formatted for slightly
  different book size

* __tex_book_list.jinja__: defines the structure for book listings in front
  and/or backmatter, works with or without images for a single series or
  multiple series (LaTeX equivalent to *book_list.jinja* HTML template)
