#!/usr/bin/env python

"""s2e.py: EPUB Pre-Processor - utilities for converting Scrivener
projects into good looking EPUBs (written for Python 3)

Run `python s2e.py -h` for more info
"""

import sys
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import argparse
from datetime import datetime as dt
from hashlib import md5
from tempfile import NamedTemporaryFile
import logging
import pandas as pd
import yaml
import jinja2 as j2
from num2eng import num2eng


_PATH_PREFIX = os.path.dirname(os.path.realpath(__file__))
_TEMPLATE_PATH = os.path.join(_PATH_PREFIX, 'tmpl')
_TEMPLATE_EXT = '.jinja'
_EPUB_SKELETON_PATH = os.path.join(_PATH_PREFIX, 'epub')
_BASIC_CH_PAR_STYLE = 'par-indent'

logging.basicConfig(level=logging.INFO)


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
            rec['IncludeInCompile'] = e.find('MetaData').findtext(
                    'IncludeInCompile')
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


def chapters_to_dict(chapters, src_dir='Files/Docs', src_type='chapter',
        headings=None, sub_headings=None, norm_level=True, key_mask=None):
    """
    Converts chapter list to dict that can be serialized as YAML for
    mainmatter.

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
        dict.
    headings: sequence
        List of chapter headings to be used.
    sub_headings: sequence
        List of chapter sub-headings to be used.
    norm_level: boolean
        If `True` level values will be shifted such that `1` becomes the
        highest level.
    key_mask: list
        If provided, only keys listed in `key_mask` will be returned for each
        list item (see below).

    Returns a list of dicts (one per chapter), keyed by (selection can be
    controlled via `key_mask` argument):

        scrivID: int
            Scrivener ID attribute value
        scrivType: str
            Scrivener 'Type' atribute ('Text' or 'Folder')
        scrivTitle: str
            Title tag text in Scrivener
        ScrivInCompile: str
            Value of Scrivener IncludeInCompile tag
        id: str
            Unique label, generated from Scrivener Title tag text
        src: str
            Path to Scrivener rtf source file
        level: int
            Level in nested Scrivener XML structure
        type: str
            Value of `src_type` argument
        heading: str
            Heading text if list with headings was provided
        subheading: str
            Subheading text if list with subheadings was provided
    """
    def fix_length(a, length, filler=''):
        if len(a) > length:
            b = a[:length]
        elif len(a) < length:
            b = a + ((length - len(a)) * [filler])
        else:
            b = a
        return b

    col_map = {'ID': 'scrivID', 'Type': 'scrivType', 'Title': 'scrivTitle',
            'Level': 'level', 'IncludeInCompile': 'scrivInCompile'}

    df = pd.DataFrame(chapters)
    df = df.rename(columns=col_map)

    df['type'] = src_type
    df['src'] = [os.path.join(src_dir, '{}.rtf'.format(i)) for i in
                      df['scrivID']]
    df['heading'] = fix_length(headings, len(df)) if headings else ''
    df['subheading'] = fix_length(
            sub_headings, len(df)) if sub_headings else ''
    if norm_level:
        df['level'] = df['level'] - df['level'].min() + 1

    ids = []
    for t in df['scrivTitle']:
        id_str = t.lower().replace(' ', '_')
        suffix = 0
        while id_str in ids:
            if suffix >= 1:
                id_str.replace('_{}'.format(suffix), '')
            suffix += 1
            id_str += '_{}'.format(suffix)
        ids.append(id_str)

    if key_mask is not None:
        drops = set(df.columns) - set(key_mask)
        df = df.drop(drops, axis=1)

    df['id'] = ids

    return df.to_dict(orient='records')


def run_script(*args):
    """
    Runs external executable `script` with list of arguments in `args`.

    Returns a tuple (stdout, stderr) with script output.
    """
    logging.debug('calling Popen with args: %s', ' '.join(args))
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()


def gen_uuid(message):
    uuid = md5(message.encode('utf-8')).hexdigest()
    return '{0}-{1}-{2}-{3}-{4}'.format(
            uuid[:8], uuid[8:12], uuid[12:16],
            uuid[16:20], uuid[20:])


def handle_init(args):
    """
    Intializes basic EPUB directory structure.
    """
    std, err = run_script('cp', '-ar', _EPUB_SKELETON_PATH, args.target)
    if err: logging.error(err.decode('utf-8'))
    if std: logging.info(std.decode('utf-8'))


def handle_scriv2md(args):
    """
    Generates markdown files from Scrivener RTF sources.

    Returns number of items written.
    """
    with open(args.mmyaml, 'r') as foi:
        mainmatter = yaml.load(foi)

    src = []
    target = []
    # quick and dirty recursion to turn yaml into lists
    def mk_mm_list(mm):
        for m in mm:
            if not m.get('src'): continue
            src.append(m['src'])
            target.append(m['id'])
            if 'children' in m:
                mk_mm_list(m['children'])

    mk_mm_list(mainmatter)

    for i, (s, t) in enumerate(zip(src, target)):
        infile = os.path.join(args.projdir, s)
        outfile = os.path.join(args.mddir, t + '.md')
        logging.info('converting %s to %s...', infile, outfile)
        cmd = os.path.join(_PATH_PREFIX, 'rtf2md.sh')
        std, err = run_script(cmd, infile, outfile)
        if err: logging.error(err.decode('utf-8'))
        if std: logging.info(std.decode('utf-8'))

    return i


def handle_scrivx2yaml(args):
    """
    Converts the 'Manuscript' section a Scrivener project XML file into a YAML
    file, augmenting with additional info such as rtf source
    file location, level, unique label.
    """
    xml_path = os.path.join(args.projdir, args.scrivxml)
    ms_bi = get_top_bi(scriv_xml=xml_path, top_title=args.toptitle)
    ch = get_chapters(top=ms_bi, type_filter=args.typefilter)

    if getattr(args, 'headings', False):
        headings = ['Chapter ' + num2eng(i + 1).title().replace(' ', '-')
                    for i in range(len(ch))]
    else:
        headings = None

    yd = chapters_to_dict(ch, src_dir=args.rtfdir, src_type=args.type,
            headings=headings, key_mask=['id', 'src', 'heading', 'level',
                                         'type'])

    foo = args.output if args.output else sys.stdout
    yaml.dump(yd, stream=foo, default_flow_style=False)
    if args.output:
            args.output.close()


def handle_genep(args):
    """
    Generates the files required for an EPUB ebook
    """
    epub_meta = {
            'opf': ('opf.jinja', os.path.join(args.htmldir, 'content.opf')),
            'ncx': ('ncx.jinja', os.path.join(args.htmldir, 'toc.ncx')),
            'toc': ('toc.jinja', os.path.join(args.htmldir, 'toc.xhtml')),
    }

    img_ext2fmt = {'jpg': 'jpeg',
            'jpeg': 'jpeg',
            'png': 'png',
            'gif': 'gif',
            'svg': 'svg'}

    with open(os.path.join(args.epubdir, args.metayaml), 'r') as foi:
        meta = yaml.load(foi)
    with open(os.path.join(args.epubdir, args.mmyaml), 'r') as foi:
        mainmatter = yaml.load(foi)

    tmplLoader = j2.FileSystemLoader(searchpath=_TEMPLATE_PATH)
    tmplEnv = j2.Environment(loader=tmplLoader, trim_blocks=True)

    # build images dict for opf manifest:
    logging.info('building image inventory...')
    img_dir = os.path.join(args.epubdir, args.imgdir)
    opf_dir = os.path.join(args.epubdir, os.path.dirname(epub_meta['opf'][1]))
    opf2img_path = os.path.relpath(img_dir, opf_dir)
    images = []
    for item in os.listdir(img_dir):
        # ignore subdirectories in image directory (can add walk later)
        if os.path.isdir(os.path.join(img_dir, item)):
            continue
        img = {}
        img['href'] = os.path.join(opf2img_path, item)
        img['id'] = '-'.join(item.split('.')[:-1]) + '-img'
        img['format'] = img_ext2fmt[item.split('.')[-1]]
        images.append(img)

    # generate metadata files:
    uuid = gen_uuid(meta.__str__() + dt.utcnow().__str__())
    kwargs = {'images': images, 'uuid': uuid}
    for tmpl_file, out_file in epub_meta.values():
        logging.info('generating %s...', out_file)
        tmpl = tmplEnv.get_template(tmpl_file)
        with open(os.path.join(args.epubdir, out_file), 'w') as foo:
            foo.write(tmpl.render(meta, mainmatter=mainmatter, **kwargs))

    # now content:
    def cp_static(pg):
        source = os.path.join(args.epubdir, args.srcdir, pg['id'] + '.xhtml')
        target = os.path.join(args.epubdir, args.htmldir, pg['id'] + '.xhtml')
        logging.info('copying %s to %s...', source, target)
        shutil.copy(source, target)

    def gen_chapter(pg):
        mdfile = os.path.join(args.epubdir, args.srcdir, pg['id'] + '.md')
        outfile = os.path.join(args.epubdir, args.htmldir, pg['id'] +
                               '.xhtml')
        par_style = pg.get('parstyle', _BASIC_CH_PAR_STYLE)
        logging.info('generating %s from %s with par style "%s"...', outfile,
                mdfile, par_style)
        cmd = os.path.join(_PATH_PREFIX, 'md2htsnip.sh')
        std, err = run_script(cmd, mdfile, par_style)
        if err: logging.error(err.decode('utf-8'))
        with open(outfile, 'w') as foo:
            foo.write(tmpl.render(pg, chapter_content=std.decode('utf-8'),
                header_title=meta['title'] + ' | ' + pg['heading']))

    fm = meta.get('frontmatter', [])
    bm = meta.get('backmatter', [])
    pages = (fm if fm else []) + (bm if bm else [])
    for pg in pages:
        if pg['type'] == 'chapter':
            gen_chapter(pg)
            continue
        elif pg['type'] == 'static':
            cp_static(pg)
            continue
        elif pg['type'] != 'template':
            continue
        tmpl_name = pg.get('template')
        if not tmpl_name:
            tmpl_name = pg['id']
        pg_data = meta.get(pg['id'])
        if not pg_data:
            # look for supplementary YAML file with page data:
            try:
                with open(os.path.join(args.epubdir, args.yincl, pg['id'] +
                    '.yaml'), 'r') as foi:
                    pg_data = yaml.load(foi)
            except FileNotFoundError as e:
                logging.warning(e)
        tmpl = tmplEnv.get_template(tmpl_name + _TEMPLATE_EXT)
        outfile = os.path.join(args.epubdir, args.htmldir, pg['id'] + '.xhtml')
        logging.info('generating %s...', outfile)
        with open(outfile, 'w') as foo:
            foo.write(tmpl.render(meta, pg_meta=pg,
                pg_data=pg_data, header_title=pg.get('heading')))

    tmpl = tmplEnv.get_template('chapter' + _TEMPLATE_EXT)

    def mm_gen(pages):
        for pg in pages:
            if pg['type'] != 'chapter':
                continue
            gen_chapter(pg)
            if 'children' in pg:
                mm_gen(pg['children'])

    mm_gen(mainmatter)

    return

def setup_parser_init(p):
    p.add_argument('--target', required=True,
            help="directory in which to set up EPUB structure")


def setup_parser_scriv2md(p):
    p.add_argument('--mmyaml', required=True,
            help="YAML file with book mainmatter page inventory")
    p.add_argument('--mddir', required=True,
            help="directory to which to write markdown output")
    p.add_argument('--projdir', required=True,
            help="path to Scrivener project directory")


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


def setup_parser_genep(p):
    p.add_argument('--metayaml', required=True,
            help="path to YAML metadata file, relative to epubdir")
    p.add_argument('--mmyaml', required=True,
            help="path to YAML mainmatter file, relative to epubdir")
    p.add_argument('--yincl', default='.',
            help="""path to YAML include directory; if genep encounters a book
            section/page with a jinja template that is different from the page
            id and the YAML file specified with `--yaml` does not contain a top
            level identifier equal to <page id>, genep will look for a file
            <page id>.yaml in <yincl> and pass the data from this file to the
            jinja template as the `pg_data` parameter; defaults to '.'""")
    p.add_argument('--epubdir', default='.',
            help="""path to EPUB root directory; defaults to '.'""")
    p.add_argument('--imgdir', default='OPS/img',
            help="""path to image directory relative to EPUB root directory;
            defaults to 'OPS/img'""")
    p.add_argument('--htmldir', default='OPS',
            help="""path to write (x)html output files to, relative to EPUB
            root directory; defaults to 'OPS'""")
    p.add_argument('--srcdir', default='src',
            help="""path to markdown and statis xhtml ource files for
            mainmatter chapter content (relative to EPUB root directory);
            dafaults to 'src'""")


# The _task_handler dictionary maps each 'command' to a (task_handler,
# parser_setup_handler) tuple.  Subparsers are initialized in __main__  (with
# the handler function's doc string as help text) and then the appropriate
# setup handler is called to add the details.
_task_handler = {'init': (handle_init, setup_parser_init),
                 'scriv2md': (handle_scriv2md, setup_parser_scriv2md),
                 'scrivx2yaml': (handle_scrivx2yaml, setup_parser_scrivx2yaml),
                 'genep': (handle_genep, setup_parser_genep),}


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