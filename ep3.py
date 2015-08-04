#!/usr/bin/env python

"""
ep3: utilities for converting Scrivener projects into good looking EPUbs
"""

# tested with Python 3.4

import sys
import os.path
import xml.etree.ElementTree as ET
import argparse
import pandas as pd
import yaml


class ParsingError(Exception):
    pass


def get_top_bi(scriv_xml='project.scrivx', top_title='Manuscript'):
    """
    Returns the first ETree 'BinderItem' element (within the first 'Binder'
    element) that includes a 'Title' tag with `top_title`. `scriv_xml` is the
    path to the Scrivener project file.

    Raises `ParsingError` if element cannot be found.
    """
    tree = ET.parse(scriv_xml)
    root = tree.getroot()
    bis = root.find('Binder').iterfind('BinderItem')
    for bi in bis:
        if bi.find('Title').text == top_title:
            return bi
    else:
        raise ParsingError('could not find Title tag containing \'{}\''.format(
            top_title))


def get_chapters(top, type_filter=None):
    """
    Returns a list if dicts with keys 'ID', 'Title', 'Type',
    'IncludeInCompile', 'Level' based on the 'BinderItem' elements under `top`.
    If `type_filter` is not `None` only elements with 'Type' tag text equal to
    `type_filter` will be considered (children will be considered in any case).
    """
    bi = []

    def get_children(top, level):
        for e in top.iterfind('BinderItem'):
            rec = {}
            rec['ID'] = e.get('ID')
            rec['Type'] = e.get('Type')
            rec['Title'] = e.findtext('Title')
            rec['IncludeInCompile'] = e.find('MetaData').findtext('IncludeInCompile')
            rec['Level'] = level
            if type_filter is None or rec['Type'] == type_filter:
                bi.append(rec)
            children = e.find('Children')
            if children is not None:
                get_children(children, level + 1)
        return

    children = top.find('Children')
    if children is not None:
        get_children(top=children, level=1)

    return bi


def chapters_to_df(chapters, src_dir='Files/Docs', src_type='content',
        headings=None, sub_headings=None, norm_level=True):
    """
    Converts chapter list to Dataframe and returns same.

    Arguments:
    ----------

    chapters: list of dicts
        List with metadate extracted from Scrivener project file. Each dict
        must be keyed by 'ID', 'Type', 'Title', 'IncludeInCompile' and 'Level'
    src_dir: str
        Path to the Scrivener (*.rtf) source files
    src_type: str
        'Type' entry to be used for these records in resulting tsv file.  Note
        that this 'Type' is different from the 'Type' in the Scrivener project
        XML file. The latter will be renamed to 'ScrivType' in the resulting
        Dataframe.
    headings: sequence
        List of chapter headings to be used.
    sub_headings: sequence
        List of chapter sub-headings to be used.
    norm_level: boolean
        If `True` level values will be shifted such that `1` becomes the
        highest level.

    Retruns a Pandas Dataframe with the following columns:

        Sequence: int
            NaN, to be added once front and back matter have been added
        ScrivSeq: int
            Seqeunce in Scrivener
        ScrivID: int
            Scrivener ID attribute value
        ScrivType: str
            Scrivener 'Type' atribute ('Text' or 'Folder')
        ScrivTitle: str
            Title tag text in Scrivener
        ScrivSrc: str
            Path to Scrivener rtf source file
        ScrivLevel: int
            Level in nested Scrivener XML structure
        ScrivInCompile: str
            Value of Scrivener IncludeInCompile tag
        ID: str
            Identifier generated from Scrivener Title
        Type: str
            Value of `src_type` argument
        Heading: str
            Heading text if `hdg_tmpl` was specified
        SubHeading: str
            Empty initially
    """
    def fix_length(a, length, filler=''):
        if len(a) > length:
            b = a[:length]
        elif len(a) < length:
            b = a + ((length - len(a)) * [filler])
        else:
            b = a
        return b



    col_map = {'ID': 'ScrivID', 'Type': 'ScrivType', 'Title': 'ScrivTitle',
            'Level': 'ScrivLevel', 'IncludeInCompile': 'ScrivInCompile'}

    df = pd.DataFrame(chapters)
    df = df.rename(columns=col_map)

    df['Type'] = src_type
    df['ScrivSeq'] = df.index + 1
    df['ScrivSrc'] = [os.path.join(src_dir, '{}.rtf'.format(i)) for i in
                      df['ScrivID']]
    df['Heading'] = fix_length(headings, len(df)) if headings else ''
    df['SubHeading'] = fix_length(sub_headings, len(df)) if sub_headings else ''
    ids = []
    for t in df['ScrivTitle']:
        id_str = t.lower().replace(' ', '_')
        suffix = 0
        while id_str in ids:
            if suffix >= 1:
                id_str.replace('_{}'.format(suffix), '')
            suffix += 1
            id_str += '_{}'.format(suffix)
        ids.append(id_str)
    df['ID'] = ids
    if norm_level:
        df['ScrivLevel'] = df['ScrivLevel'] - df['ScrivLevel'].min() + 1

    return df.set_index('ScrivSeq', drop=True)


def handle_scriv2tsv(args):
    """
    Converts the 'Manuscript' section a Scrivener project XML file into tab
    separated records, augmenting same with additional info such as rtf source
    file location, level and sequencs numbers.
    """
    xml_path = os.path.join(args.projdir, args.scrivxml)
    ms_bi = get_top_bi(scriv_xml=xml_path, top_title=args.toptitle)
    ch = get_chapters(top=ms_bi, type_filter=args.typefilter)
    # if meta file exists read and check for headings and subheadings
    if args.meta:
        meta = yaml.load(args.meta)
        args.meta.close()
        headings = meta.get('headings')
        sub_headings = meta.get('sub-headings')
    else:
        headings = sub_headings = None
    df = chapters_to_df(ch, src_dir=args.rtfdir, src_type=args.type,
            headings=headings, sub_headings=sub_headings)

    foo = args.output if args.output else sys.stdout
    df.to_csv(foo, sep='\t')
    if args.output:
            args.output.close()


def handle_genep(args):
    """
    Generates the files required for an EPUB ebook
    """
    pass


def setup_parser_scriv2tsv(p):
    p.add_argument('--projdir', help="path to Scrivener project directory")
    p.add_argument('--scrivxml', default='project.scrivx',
            help="Scrivener project XML file, relative to Scrivener project"
            " directory; defaults to 'project.scrivx'")
    p.add_argument('--rtfdir', default='Files/Docs',
            help="path to Scrivener rtf directory, relative to Scrivener"
            " project directory; defaults to 'Files/Docs'")
    p.add_argument('--output', type=argparse.FileType('w'), default=None,
            help="file to save tab separated output to, defaults to STDOUT if"
            " not specified")
    p.add_argument('--meta', type=argparse.FileType('r'), default=None,
            help="YAML metadata file")
    p.add_argument('--type', default='content',
            help="string to used as 'Type' attribute for chapters; "
            "defaults to 'content'")
    p.add_argument('--toptitle', default='Manuscript',
            help="Title element text of the top BinderItem to be used from"
            " Scrivener project file, defaults to 'Manuscript'")
    p.add_argument('--typefilter', default=None,
            help="Title element text of the top BinderItem to be used from"
            " Scrivener project file")


def setup_parser_genep(p):
    pass


# The _task_handler dictionary maps each 'command' to a (task_handler,
# parser_setup_handler) tuple.  Subparsers are initialized in __main__  (with
# the handler function's doc string as help text) and then the appropriate
# setup handler is called to add the details.
_task_handler = {'scriv2tsv': (handle_scriv2tsv, setup_parser_scriv2tsv),
                 'genep': (handle_genep, setup_parser_genep),}


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
            description="""
            {}: EPUB pre-processing - utilities to turn Scrivener project into
            an EPUB ebook
            """.format(__file__))

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
