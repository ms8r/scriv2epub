#!/usr/bin/env python

"""
s2e.py: EPUB Pre-Processor - utilities for converting Scrivener
projects into good looking EPUBs and print books(written for Python 3)

Run `python s2e.py -h` for more info
"""

import argparse
import logging

from pypub import epub, scriv, latex


logging.basicConfig(level=logging.INFO)

def setup_parser_init(p):
    p.add_argument('--target', default='.',
            help="""directory in which to set up EPUB structure; defaults to
            current directory""")


def setup_parser_scriv2md(p):
    p.add_argument('--mmyaml', required=True,
            help="YAML file with book mainmatter page inventory")
    p.add_argument('--mddir', required=True,
            help="directory to which to write markdown output")
    p.add_argument('--projdir', required=True,
            help="path to Scrivener project directory")


def setup_parser_mmcat(p):
    p.add_argument('--mmyaml', required=True,
            help="YAML file with book mainmatter page inventory")
    p.add_argument('--outfile', type=argparse.FileType('a'), default=None,
            help="file to save output to, defaults to STDOUT if"
            " not specified")
    p.add_argument('--hoffset', type=int, default=0,
            help="""offset for chapter heading level; defaults to 0""")
    p.add_argument('--mddir', required=True,
            help="directory from which to read markdown chapter files")
    p.add_argument('--lbreak', action='store_true',
            help="""will replace '***' and '###' (also if escaped and/or
                 space spearated) with LaTeX code for a paragraph separator
                 (fleuron)""")


def setup_parser_body2md(p):
    p.add_argument('--bodydir', default='.',
            help="""path to body XHTML files; defaults to current
                 directory""")
    p.add_argument('--yamlout', type=argparse.FileType('w'), default=None,
            help="file to save YAML output to, defaults to STDOUT if"
            " not specified")
    p.add_argument('--startnum', type=int, required=True,
            help="first html body file number to process")
    p.add_argument('--stopnum', type=int, required=True,
            help="last html body file number to process")
    p.add_argument('--mdprefix', default='',
            help="""prefix to use for generated Markdown files; defaults to
            ''""")
    p.add_argument('--headings', action='store_true',
            help="will add headings to for each chapter as 'Chapter Num'")
    p.add_argument('--hoffset', type=int, default=0,
            help="""offset for start of chapter headings (first <hoffset>
            chapters will be skipped); defaults to 0""")


def setup_parser_scrivx2yaml(p):
    p.add_argument('--projdir', required=True,
            help="path to Scrivener project directory")
    p.add_argument('--scrivxml', default='project.scrivx',
            help="Scrivener project XML file, relative to Scrivener project"
            " directory; defaults to 'project.scrivx'")
    p.add_argument('--rtfdir', default='Files/Docs',
            help="path to Scrivener rtf directory, relative to Scrivener"
            " project directory; defaults to 'Files/Docs'")
    p.add_argument('--output', type=argparse.FileType('w'), default=None,
            help="file to save YAML output to, defaults to STDOUT if"
            " not specified")
    p.add_argument('--type', default='chapter',
            help="string to used as 'Type' attribute for chapters; "
            "defaults to 'chapter'")
    p.add_argument('--toptitle', default='Manuscript',
            help="Title element text of the top BinderItem to be used from"
            " Scrivener project file, defaults to 'Manuscript'")
    p.add_argument('--typefilter', default=None,
            help="Title element text of the top BinderItem to be used from"
            " Scrivener project file")
    p.add_argument('--headings', action='store_true',
            help="will add headings to for each chapter as 'Chapter Num'")
    p.add_argument('--hoffset', type=int, default=0,
            help="""offset for start of chapter headings (first <hoffset>
            chapters will be skipped""")


def setup_parser_genlatex(p):
    p.add_argument('--metayaml', required=True,
            help="path to YAML metadata file")
    p.add_argument('--yincl', default='.',
            help="""path to YAML include directory; if genlatex encounters a
                 book section/page with a jinja template that is different
                 from the page id and the YAML file specified with `--yaml`
                 does not contain a top level identifier equal to <page id>,
                 genlatex will look for a file <page id>.yaml in <yincl> and
                 pass the data from this file to the jinja template as the
                 `pg_data` parameter; defaults to '.'""")
    p.add_argument('--tmpl', default='tex_book_5x8',
            help="template to use for the book")
    p.add_argument('--book', required=True,
            help="file name to be used for LaTeX output (without extension")


def setup_parser_genep(p):
    p.add_argument('--metayaml', required=True,
            help="path to YAML metadata file, relative to epubdir")
    p.add_argument('--mmyaml', required=True,
            help="path to YAML mainmatter file, relative to epubdir")
    p.add_argument('--yincl', default='.',
            help="""path to YAML include directory; if genep encounters a
                 book section/page with a jinja template that is different
                 from the page id and the YAML file specified with `--yaml`
                 does not contain a top level identifier equal to <page id>,
                 genep will look for a file <page id>.yaml in <yincl> and
                 pass the data from this file to the jinja template as the
                 `pg_data` parameter; defaults to '.'""")
    p.add_argument('--epubdir', default='.',
            help="""path to EPUB root directory; defaults to '.'""")
    p.add_argument('--imgdir', default='OPS/img',
            help="""path to image directory relative to EPUB root directory;
            defaults to 'OPS/img'""")
    p.add_argument('--htmldir', default='OPS',
            help="""path to write (x)html output files to, relative to EPUB
            root directory; defaults to 'OPS'""")
    p.add_argument('--srcdir', default='src',
            help="""path to markdown and static xhtml ource files for
            mainmatter chapter content (relative to EPUB root directory);
            dafaults to 'src'""")
    p.add_argument('--dropcaps', action='store_true',
            help="""causes first character in chapters to be formatted
            as dropcap""")


def handle_mmcat(args):
    """
    Concatenates all mainmatter markdown sources with headings at correct
    level inserted.
    """
    latex.mmcat(args.mmyaml, args.outfile, args.mddir, args.hoffset,
            args.lbreak)


def handle_genlatex(args):
    """
    Generates LaTeX for a print book, given meta YAML, mainmatter md and a
    template.
    """
    latex.mkbook(args.metayaml, args.book, args.tmpl)


def handle_scriv2md(args):
    """
    Generates markdown files from Scrivener RTF sources.

    Returns number of items written.
    """
    pypup.scriv.to_md(args.mmyaml, args.projdir, args.mddir)


def handle_scrivx2yaml(args):
    """
    Converts the 'Manuscript' section a Scrivener project XML file into a
    YAML file, augmenting with additional info such as rtf source file
    location and unique label.
    """
    pypup.scriv.to_yaml(args.projdir, args.scrivxml, args.rtfdir,
            args.toptitle, args.typefilter, args.type, args.hoffset,
            args.output)


def handle_body2md(args):
    """
    Converts a set of body XHTML files (already "<em></em> cleansed") into
    Markdown files and creates YAML mainmatter output. Optionally headings of
    the format 'Chapter <Num>' can be added.

    Returns the list with mainmatter dicts.

    NOTE: this is quick and dirty and specific to ALB
    """
    pypup.scriv.body2md(args.bodydir, args.startnum, args.stopnum,
            args.mdprefix, args.hoffset, args.yamlout)


def handle_init(args):
    """
    Intializes basic EPUB directory structure.
    """
    epub.init(args.target)


def handle_genep(args):
    """
    Generates the files required for an EPUB ebook
    """
    epub.mkbook(args.epubdir, args.srcdir, args.htmldir, args.imgdir,
            args.metayaml, args.mmyaml, args.yincl, args.dropcaps)


# The _task_handler dictionary maps each 'command' to a (task_handler,
# parser_setup_handler) tuple.  Subparsers are initialized in __main__  (with
# the handler function's doc string as help text) and then the appropriate
# setup handler is called to add the details.
_task_handler = {'init':        (handle_init, setup_parser_init),
                 'scriv2md':    (handle_scriv2md, setup_parser_scriv2md),
                 'scrivx2yaml': (handle_scrivx2yaml,
                                 setup_parser_scrivx2yaml),
                 'genep':       (handle_genep, setup_parser_genep),
                 'genlatex':    (handle_genlatex, setup_parser_genlatex),
                 'body2md':     (handle_body2md, setup_parser_body2md),
                 'mmcat':       (handle_mmcat, setup_parser_mmcat),
}


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=__doc__)

    # add subparser for each task
    subparsers = parser.add_subparsers()
    for k in _task_handler:
        func, p_setup = _task_handler[k]
        p = subparsers.add_parser(k, help=func.__doc__)
        p.set_defaults(func=func)
        p_setup(p)

    # parse the arguments and run the handler associated with each task
    args = parser.parse_args()
    args.func(args)
