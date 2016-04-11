import xml.etree.ElementTree as ET
import re
import os.path
from copy import deepcopy
import logging

from . import params
from . import utils


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
                    and (in_compile is None or in_compile.lower() == 'yes'
                         or not in_compile_only)):
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


def chapters_to_dict(chapters, src_dir='Files/Docs', src_type='chapter',
                     headings=None, sub_headings=None, in_place=False):
    """
    Converts chapter list to dict that can be serialized as YAML for
    mainmatter.

    Arguments:
    ----------

    chapters: list of dicts
        List with metadate extracted from Scrivener project file. Each dict
        must be keyed by 'scrivID', 'scrivType', 'scrivTitle', and potentially
        'children'
    src_dir: str
        Relative path to RFT files from Scrivener project dir.
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
            ch['rtf_src'] = os.path.join(src_dir,
                                         '{}.rtf'.format(ch['scrivID']))
            ch.pop('scrivID', None)
            ch['heading'] =  headings.pop(0) if headings else ''
            ch['subheading'] =  sub_headings.pop(0) if sub_headings else ''
            if 'children' in ch:
                augment_ch(ch['children'])

    augment_ch(chapters)

    return chapters


def to_md(mmyaml, projdir, mddir):
    """
    Generates markdown files from Scrivener RTF sources.

    Returns number of items written.
    """
    with open(mmyaml, 'r') as foi:
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
        infile = os.path.join(projdir, s)
        outfile = os.path.join(mddir, t + '.md')
        logging.info('converting %s to %s...', infile, outfile)
        cmd = os.path.join(params._PATH_PREFIX, 'rtf2md.sh')
        std, err = utils.run_script(cmd, infile, outfile)
        if err: logging.error(err.decode('utf-8'))
        if std: logging.info(std.decode('utf-8'))

    return i


def to_yaml(projdir, scrivxml, rtfdir, toptitle, typefilter, src_type, hoffset,
        headings, output):
    """
    Converts the 'Manuscript' section a Scrivener project XML file into a YAML
    file, augmenting with additional info such as rtf source
    file location and unique label.
    """
    xml_path = os.path.join(projdir, scrivxml)
    ms_bi = get_top_bi(scriv_xml=xml_path, top_title=toptitle)
    ch, count = get_chapters(top=ms_bi, type_filter=typefilter)

    if headings:
        headings = hoffset * ['']
        headings += ['Chapter ' + utils.num2eng(i + 1).title().replace(' ', '-')
                     for i in range(count - hoffset)]
    else:
        headings = None

    chapters_to_dict(ch, src_dir=rtfdir, src_type=src_type,
                     headings=headings, in_place=True)

    foo = output if output else sys.stdout
    yaml.dump(ch, stream=foo, default_flow_style=False)
    if output:
            output.close()


def body2md(bodydir, startnum, stopnum, mdprefix, hoffset, headings, yamlout):
    """
    Converts a set of body XHTML files (already "<em></em> cleansed") into
    Markdown files and creates YAML mainmatter output. Optionally headings of
    the format 'Chapter <Num>' can be added.

    Returns the list with mainmatter dicts.

    NOTE: this is quick and dirty and specific to ALB
    """
    num_files = stopnum - startnum + 1
    if headings:
        headings = hoffset * ['']
        headings += ['Chapter ' + utils.num2eng(i + 1).title().replace(' ', '-')
                     for i in range(num_files - hoffset)]
    else:
        headings = num_files * ['']

    cmd = os.path.join(params._PATH_PREFIX, 'body2md.sh')
    std, err = utils.run_script(cmd, bodydir, str(startnum),
                          str(stopnum), mdprefix)
    if err: logging.error(err.decode('utf-8'))
    if std: logging.info(std.decode('utf-8'))

    # generate mainmatter YAML:
    mm = []
    for i, hdg in enumerate(headings):
        rec = {}
        rec['id'] = mdprefix + 'body{}'.format(i + 1)
        rec['type'] = 'chapter'
        rec['heading'] = hdg
        mm.append(rec)

    foo = yamlout if yamlout else sys.stdout
    yaml.dump(mm, stream=foo, default_flow_style=False)
    if yamlout:
            yamlout.close()

    return mm


