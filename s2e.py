#!/usr/bin/env python

"""s2e.py: EPUB Pre-Processor - utilities for converting Scrivener
projects into good looking EPUBs (written for Python 3)

Run `python s2e.py -h` for more info
"""

import sys
import os
import shutil
import subprocess
import re
from copy import deepcopy
import xml.etree.ElementTree as ET
import argparse
from datetime import datetime as dt
from hashlib import md5
from tempfile import NamedTemporaryFile
import logging
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


def get_chapters(top, type_filter=None, in_compile_only=True):
    """
    Returns a tuple `(chapters, count)`. `chapters` is a list of dicts with
    keys 'scrivID', 'scrivTitle', 'scrivType', 'IncludeInCompile' based on the
    'BinderItem' elements under `top`. If the respective element has children
    these will be captured in a list, mapped against 'children'.  If
    `type_filter` is not `None` only elements with 'Type' tag text equal to
    `type_filter` will be considered (children will be considered in any case).
    Similarly, if `in_compile_only` is `True` only items for which the
    'IncludeInCompile' value is 'Yes' will be considered. `count` is the total
    number of items in `chapters` across potential nestings.
    """
    def get_children(top, chapters):
        count = 0
        for e in top.iterfind('BinderItem'):
            rec = {}
            rec['scrivID'] = e.get('ID')
            rec['scrivType'] = e.get('Type')
            rec['scrivTitle'] = e.findtext('Title')
            in_compile = e.find('MetaData').findtext(
                    'IncludeInCompile')
            if ((type_filter is None or rec['scrivType'] == type_filter)
                    and (in_compile.lower() == 'yes' or not in_compile_only)):
                incl_item = True
                rec['children'] = []
                ccollect = rec['children']
            else:
                # we're not interested in the current item but want to pull
                # up its children one level
                incl_item = False
                ccollect = chapters
            children = e.find('Children')
            if children is not None:
                    count += get_children(children, ccollect)
            if incl_item:
                if len(rec['children']) == 0:
                    rec.pop('children', None)
                chapters.append(rec)
                count += 1
        return count

    children = top.find('Children')

    chapters = []
    count = 0
    if children is not None:
        count = get_children(top=children, chapters=chapters)

    return (chapters, count)


def chapters_to_dict(chapters, src_type='chapter', headings=None,
                     sub_headings=None, in_place=False):
    """
    Converts chapter list to dict that can be serialized as YAML for
    mainmatter.

    Arguments:
    ----------

    chapters: list of dicts
        List with metadate extracted from Scrivener project file. Each dict
        must be keyed by 'scrivID', 'scrivType', 'scrivTitle', and potentially
        'children'
    src_type: str
        'type' entry to be used for these records in resulting dict.
    headings: sequence
        List of chapter headings to be used. These will be used in sequence
        across potentially nested structures in `chapters`.
    sub_headings: sequence
        List of chapter sub-headings to be used. These will be used in sequence
        across potentially nested structures in `chapters`.

    Returns `chapters`, augmented by the keys below, but with key 'scrivID'
    removed. If `in_place` is `False` an augmented copy of `chapters` will be
    returned.

        id: str
            Unique label, generated from Scrivener Title tag text
        rtf_src: str
            Path to Scrivener rtf source file
        type: str
            Value of `src_type` argument
        heading: str
            Heading text if list with headings was provided
        subheading: str
            Subheading text if list with subheadings was provided
        scrivType: str
            Scrivener 'Type' atribute ('Text' or 'Folder')
        scrivTitle: str
            Title tag text in Scrivener
    """
    if not in_place: chapters = deepcopy(chapters)
    if headings: headings = headings[:]
    if sub_headings: sub_headings = sub_headings[:]
    ids = set()

    def augment_ch(chapters):
        for ch in chapters:
            id_str = ch['scrivTitle'].lower()
            id_str = re.sub(r'[ \-&]', '_', id_str)
            id_str = re.sub(r'[,.;:\"\'*#@%!$?]', '', id_str)
            suffix = 0
            while id_str in ids:
                if suffix >= 1:
                    id_str.replace('_{}'.format(suffix), '')
                suffix += 1
                id_str += '_{}'.format(suffix)
            ids.add(id_str)
            ch['id'] = id_str
            ch['type'] = src_type
            ch['rtf_src'] = '{}.rtf'.format(ch['scrivID'])
            ch.pop('scrivID', None)
            ch['heading'] =  headings.pop(0) if headings else ''
            ch['subheading'] =  sub_headings.pop(0) if sub_headings else ''
            if 'children' in ch:
                augment_ch(ch['children'])

    augment_ch(chapters)

    return chapters


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
            if not m.get('rtf_src'): continue
            src.append(m['rtf_src'])
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
    file location and unique label.
    """
    xml_path = os.path.join(args.projdir, args.scrivxml)
    ms_bi = get_top_bi(scriv_xml=xml_path, top_title=args.toptitle)
    ch, count = get_chapters(top=ms_bi, type_filter=args.typefilter)

    if getattr(args, 'headings', False):
        headings = args.hoffset * ['']
        headings += ['Chapter ' + num2eng(i + 1).title().replace(' ', '-')
                     for i in range(count - args.hoffset)]
    else:
        headings = None

    chapters_to_dict(ch, src_dir=args.rtfdir, src_type=args.type,
                     headings=headings, in_place=True,
                     level_offset=args.loffset)

    foo = args.output if args.output else sys.stdout
    yaml.dump(ch, stream=foo, default_flow_style=False)
    if args.output:
            args.output.close()


def handle_body2md(args):
    """
    Converts a set of body XHTML files (already "<em></em> cleansed") into
    Markdown files and creates YAML mainmatter output. Optionally headings of
    the format 'Chapter <Num>' can be added.

    Returns the list with mainmatter dicts.

    NOTE: this is quick and dirty and specific to ALB
    """
    num_files = args.stopnum - args.startnum + 1
    if getattr(args, 'headings', False):
        headings = args.hoffset * ['']
        headings += ['Chapter ' + num2eng(i + 1).title().replace(' ', '-')
                     for i in range(num_files - args.hoffset)]
    else:
        headings = num_files * ['']

    cmd = os.path.join(_PATH_PREFIX, 'body2md.sh')
    std, err = run_script(cmd, args.bodydir, str(args.startnum),
                          str(args.stopnum), args.mdprefix)
    if err: logging.error(err.decode('utf-8'))
    if std: logging.info(std.decode('utf-8'))

    # generate mainmatter YAML:
    mm = []
    for i, hdg in enumerate(headings):
        rec = {}
        rec['id'] = args.mdprefix + 'body{}'.format(i + 1)
        rec['type'] = 'chapter'
        rec['heading'] = hdg
        mm.append(rec)

    foo = args.yamlout if args.yamlout else sys.stdout
    yaml.dump(mm, stream=foo, default_flow_style=False)
    if args.yamlout:
            args.yamlout.close()

    return mm


def handle_genep(args):
    """
    Generates the files required for an EPUB ebook
    """
    epub_meta = {
            'opf': ('opf.jinja', os.path.join(args.htmldir, 'content.opf')),
            'ncx': ('ncx.jinja', os.path.join(args.htmldir, 'toc.ncx')),
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
        img['format'] = img_ext2fmt[item.split('.')[-1].lower()]
        images.append(img)

    fm = meta.get('frontmatter', [])
    bm = meta.get('backmatter', [])
    pages = (fm if fm else []) + mainmatter + (bm if bm else [])

    # generate metadata files:
    uuid = gen_uuid(meta.__str__() + dt.utcnow().__str__())
    kwargs = {'images': images, 'uuid': uuid}
    for tmpl_file, out_file in epub_meta.values():
        logging.info('generating %s...', out_file)
        tmpl = tmplEnv.get_template(tmpl_file)
        with open(os.path.join(args.epubdir, out_file), 'w') as foo:
            foo.write(tmpl.render(meta, pages=pages, **kwargs))

    # now content:
    def cp_static(pg):
        src_base = pg.get('src', pg['id'])
        source = os.path.join(args.epubdir, args.srcdir, src_base + '.xhtml')
        target = os.path.join(args.epubdir, args.htmldir, pg['id'] + '.xhtml')
        logging.info('copying %s to %s...', source, target)
        shutil.copy(source, target)

    def gen_chapter(pg):
        md_base = pg.get('src', pg['id'])
        mdfile = os.path.join(args.epubdir, args.srcdir, md_base + '.md')
        outfile = os.path.join(args.epubdir, args.htmldir, pg['id'] +
                               '.xhtml')
        par_style = pg.get('parstyle', _BASIC_CH_PAR_STYLE)
        logging.info('generating %s from %s with par style "%s"...', outfile,
                mdfile, par_style)
        cmd = os.path.join(_PATH_PREFIX, 'md2htsnip.sh')
        std, err = run_script(cmd, mdfile, par_style)
        if err: logging.error(err.decode('utf-8'))
        tmpl_name = pg.get('template', 'chapter')
        tmpl = tmplEnv.get_template(tmpl_name + _TEMPLATE_EXT)
        with open(outfile, 'w') as foo:
            foo.write(tmpl.render(pg, chapter_content=std.decode('utf-8'),
                header_title=meta['title'] + ' | ' + pg['heading']))

    def gen_from_tmpl(pg, pages):
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
                pg_data=pg_data, pages=pages,
                header_title=pg.get('heading')))

    def gen_content(pages):
        for pg in pages:
            if pg['type'] == 'chapter':
                gen_chapter(pg)
            elif pg['type'] == 'static':
                cp_static(pg)
            elif pg['type'] == 'template':
                gen_from_tmpl(pg, pages)
            if 'children' in pg:
                gen_content(pg['children'])

    gen_content(pages)

    return

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


def setup_parser_body2md(p):
    p.add_argument('--bodydir', default='.',
            help="""path to body XHTML files; defaults to current directory""")
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
                 'genep': (handle_genep, setup_parser_genep),
                 'body2md': (handle_body2md, setup_parser_body2md),}


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
