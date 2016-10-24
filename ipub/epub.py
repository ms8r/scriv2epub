"""
EPUB generation from Markdown source files plus YAML metadata
"""

import os
from datetime import datetime as dt
import shutil
from hashlib import md5
import logging
import re
import yaml
import jinja2 as j2
import markdown

from . import params
from . import utils


def gen_uuid(message):
    uuid = md5(message.encode('utf-8')).hexdigest()
    return '{0}-{1}-{2}-{3}-{4}'.format(
            uuid[:8], uuid[8:12], uuid[12:16],
            uuid[16:20], uuid[20:])


def init(target):
    """
    Intializes basic EPUB directory structure.
    """
    std, err = utils.run_script('cp', '-ar', params._EPUB_SKELETON_PATH,
                                target)
    if err: logging.error(err.decode('utf-8'))
    if std: logging.info(std.decode('utf-8'))


def navMap2dict(nav_map, chtype='chapter', headings=False, hoffset=0):
    """
    Converts the NCX navMap (an ETree Element) to a list of dicts, preserving
    hierarchy/nesting. Returns number of navPoints  added (incl. nesting).
    The value of `chtype` will be added a 'type' entry to each navPoint in the
    output. If `headings == True`, the 'heading 'entry for each navPoint will
    the chapter number in English ("Chapter One"). `hoffset` can be used to
    specify an offset in the chapter numbering. if `hoffset > 0`, numbering
    will start with the value of `hoffset`. If `hoffset < 0`, numbering will
    start with One at the (hoffset + 1)st chapter.
    """
    # extract name space URI (if any)
    try:
        ns_uri = re.match(r'\{([^}]+)\}', nav_map.tag).groups()[0]
    except AttributeError:
        ns_uri = ''

    ns = {'xmlns': ns_uri}

    def get_navPoint_children(parent, records, count):
        for np in parent.iterfind('xmlns:navPoint', ns):
            count += 1
            rec = {}
            if headings and count > 0:
                rec['heading'] = ('Chapter ' +
                        num2eng(count).title().replace(' ', '-'))
            else:
                rec['heading'] = np.find(
                        'xmlns:navLabel', ns).find('xmlns:text', ns).text
            rec['id'] = np.get('id')
            rec['type'] = chtype
            rec['src'] = np.find('xmlns:content', ns).get('src')
            # check for children:
            if np.find('xmlns:navPoint', ns):
                children = []
                count = get_navPoint_children(np, children, count)
                rec['children'] = children
            records.append(rec)
        return count

    records = []
    get_navPoint_children(nav_map, records, hoffset)

    return records


def build_img_inventory(epubdir, imgdir, opfdir):
    """
    Build list of image dicts for opf manifest.
    """
    img_ext2fmt = {'jpg': 'jpeg',
                   'jpeg': 'jpeg',
                   'png': 'png',
                   'gif': 'gif',
                   'svg': 'svg+xml'}

    logging.info('building image inventory...')
    img_dir = os.path.join(epubdir, imgdir)
    opf_dir = os.path.join(epubdir, os.path.dirname(opfdir))
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

    return images


def render_output(tmpl_env, tmpl_name, out_file=None, **kwargs):
    """
    Renders output from template with option to write to file.

    Args:
        tmpl_env: jinja Environment object to be used to get `tmpl_file`
        tmpl_name (str): name of the jinja template file to use (without
            extension)
        out_file (str): path to output file to be generated: if `None` rendered
            string will be returned.

        Additional file specific kwargs may be required, depending on template.

    Returns:
        Rendered text as string if `out_file` is `None`. Otherwise length of
        string written to `out_file`.
    """
    tmpl = tmpl_env.get_template(tmpl_name + params._TEMPLATE_EXT)
    text = tmpl.render(**kwargs)
    if not out_file:
        return text
    with open(out_file, 'w') as foo:
        logging.info('generating %s...', out_file)
        foo.write(text)
    return len(text)


def cp_static(pg, epubdir, srcdir, htmldir, **kwargs):
    """
    Copies static source file to htmldir, inserting url query params if
    specified in `pg`.
    """
    src_base = pg.get('src', pg['id'])
    source = os.path.join(epubdir, srcdir, src_base + '.xhtml')
    target = os.path.join(epubdir, htmldir, pg['id'] + '.xhtml')
    logging.info('copying %s to %s...', source, target)
    shutil.copy(source, target)
    if 'query_url' in pg:
        with open(target, 'r') as foi:
            ht_text = utils.mk_query_urls(foi.read(),
                    pg['query_url']['url_re'], pg['query_url']['utm'])
        with open(target, 'w') as foo:
            foo.write(ht_text)


def gen_chapter(pg, meta, tmpl_env, epubdir, srcdir, htmldir, dropcaps,
                **kwargs):
    """
    Generates HTML chapter file from md source.
    """
    # lines with `break_re` in the raw HTML output will be styled as in-page
    # section breaks
    break_re = [r'&lt;&lt;&lt;\s*&gt;&gt;&gt;',
                r'\*\s*\*\s*\*',
                r'#\s*#\s*#', ]

    # TODO: run beg_raw and end_raw through markdown
    outfile = os.path.join(epubdir, htmldir, pg['id'] +
                           '.xhtml')
    logging.info('generating %s from %s with par style "%s"...', outfile,
            pg['mdfile'], pg['parstyle'])
    with open(pg['mdfile'], 'r') as foi:
        ht_text = markdown.markdown(foi.read(), extensions=['meta', 'smarty'])
    # styling for in-page section breaks:
    for pat in break_re:
        pat = r'<p>\s*(?P<first>{})\s*</p>'.format(pat)
        ht_text = re.sub(
                pat, '<p class="{}">\g<first></p>'.format(
                params._IN_PG_SEC_BREAK_STYLE), ht_text)
    ht_text = re.sub(r'<p>', r'<p class="{}">'.format(pg['parstyle']), ht_text)
    if dropcaps:
        ht_text = re.sub(
                r'<p class="{}">\s*'
                '(?P<pre_tag>(<[^>]*>)*)'
                '(?P<first>[^a-zA-Z0-9]*[a-zA-Z0-9])'.format(
                    params._BASIC_CH_PAR_STYLE),
                '<p class="{0}">\g<pre_tag><span class="{1}">'
                '\g<first></span>'.format(params._FIRST_CH_PAR_STYLE,
                    params._DROP_CAP_STYLE), ht_text, 1)
        ht_text = re.sub(r'<p class="{}">'.format(
                params._BASIC_CH_PAR_STYLE),
                '<p class="{0} {1}">'.format(params._BASIC_CH_PAR_STYLE,
                params._CLEAR_STYLE), ht_text, 1)
    header_title = meta['title']
    if pg.get('heading'):
        header_title += ' | ' + pg['heading']
    tmpl_name = pg.get('template', 'chapter')
    ht_text = render_output(tmpl_env, tmpl_name, chapter_content=ht_text,
                            header_title=header_title, pg_meta=pg)
    if 'query_url' in pg:
        ht_text = utils.mk_query_urls(ht_text, pg['query_url']['url_re'],
                                      pg['query_url']['utm'])
    with open(outfile, 'w') as foo:
        foo.write(ht_text)


def gen_from_tmpl(pg, pages, meta, tmpl_env, epubdir, srcdir, htmldir,
                  yaml_incl_dir, **kwargs):
    """
    Generates HTML output from (page-) metadata
    """
    tmpl_name = pg.get('template')
    if not tmpl_name:
        tmpl_name = pg['id']
    pg_data = meta.get(pg['id'])
    if not pg_data:
        # look for supplementary YAML file with page data,
        # first in current dir, then in epubdir, then in yincl:
        try:
            with open(pg['id'] + '.yaml', 'r') as foi:
                pg_data = yaml.load(foi)
        except FileNotFoundError as e:
            logging.warning(e)
        try:
            with open(os.path.join(epubdir, pg['id'] + '.yaml'),
                      'r') as foi:
                pg_data = yaml.load(foi)
        except FileNotFoundError as e:
            logging.warning(e)
        try:
            with open(os.path.join(yaml_incl_dir, pg['id'] +
                      '.yaml'), 'r') as foi:
                pg_data = yaml.load(foi)
        except FileNotFoundError as e:
            logging.warning(e)
    ht_text = render_output(tmpl_env, tmpl_name, pg_meta=pg,
            pg_data=pg_data, pages=pages, header_title=pg.get('heading'),
            **meta)
    if 'query_url' in pg:
        ht_text = utils.mk_query_urls(ht_text, pg['query_url']['url_re'],
                                      pg['query_url']['utm'])
    outfile = os.path.join(epubdir, htmldir, pg['id'] + '.xhtml')
    logging.info('generating %s...', outfile)
    with open(outfile, 'w') as foo:
        foo.write(ht_text)


def augment_meta(meta_item, epubdir, srcdir):
    """
    Augment with metadata defined in individual source files for entries of
    type 'chapter'.
    """
    item = meta_item.copy()
    if item['type'] != 'chapter':
        return item
    # Page level metadata items for which the chapter template expects single
    # values rather than lists (need to be extracted from lists if defined in
    # sourve pages):
    delist = ['heading', 'subheading', 'hdgalign', 'subalign', 'beg_raw',
              'end_raw']
    md = markdown.Markdown(extensions=['meta'])
    src_dir = item.get('srcdir')
    src_path = os.path.join(epubdir, src_dir if src_dir else
                            srcdir)
    src_path = os.path.abspath(src_path)
    md_base = item.get('src', item['id'])
    mdfile = os.path.join(src_path, md_base + '.md')
    # Note: the following will change the item in `mainmatter` list
    item['mdfile'] = mdfile
    item['parstyle'] = item.get('parstyle', params._BASIC_CH_PAR_STYLE)
    with open(mdfile, 'r') as foi:
        # we're only interested in metadata, throw away html:
        md.convert(foi.read())
    mdm = { key: value[0] if key in delist else value
                     for key, value in md.Meta.items()}
    item = utils.merge_dicts(mdm, item)

    return item


def get_meta(epubdir, yaml_meta, srcdir):
    """
    Generates metayaml list augmenting ``yaml_meta`` with page metadata
    contained in individual source files (*.md) for pages of type 'chapter'.

    Will also add an 'mdfile' key for each mainmatter item that has the full
    absolute path to the corresponding Markdown source file. Similarly, the
    'parstyle' value will be defined for each item.
    """

    def genmeta(mm_list):
        out = []
        for item in mm_list:
            if 'children' in item:
                item['children'] = genmeta(item['children'])
            out.append(augment_meta(item, epubdir, srcdir))
        return out

    return genmeta(yaml_meta)


def md2ht(text, par_style=None, trim_tags=False):
    """
    Converts Markdown `text` to HTML, optionally stripping outer <p>/<h.> and
    </p>/</h> tags ('trim_tags=True`, works for single paragrpahs only).
    `par_style` can be used to specify a CSS class which will be added as an
    attribute to remaining `<p>` tags. Uses smartypants and will leave input
    HTML untouched.
    """
    # remove '</p> <p>' spaces which seem to trip up markdown
    text = re.sub(r'</p\s*>\s+<p', '</p><p', text)

    html = markdown.markdown(text, extensions=['smarty'])
    if trim_tags:
        html = re.match(r'^\s*<[ph][^>]*>(.*)</[ph]\s*>\s*$', html,
                        flags=re.MULTILINE + re.DOTALL).group(1)
    if par_style:
        html = html.replace('<p>', '<p class="%s">' % par_style)

    return html


def mkbook(epubdir, srcdir, htmldir, imgdir, metayaml, mmyaml, yaml_incl_dir,
           dropcaps=False):
    """
    Generates the files required for an EPUB ebook
    """
    epub_meta = {
            # maps meta type to (template, output_path)
            'opf': ('opf', os.path.join(htmldir, 'content.opf')),
            'ncx': ('ncx', os.path.join(htmldir, 'toc.ncx')),
    }

    with open(os.path.join(epubdir, metayaml), 'r') as foi:
        meta = yaml.load(foi)
    fm = get_meta(epubdir, meta.get('frontmatter', []), srcdir)
    bm = get_meta(epubdir, meta.get('backmatter', []), srcdir)
    with open(os.path.join(epubdir, mmyaml), 'r') as foi:
        mainmatter = yaml.load(foi)
    mm = get_meta(epubdir, mainmatter, srcdir)
    pages = (fm if fm else []) + mm + (bm if bm else [])

    tmplLoader = j2.FileSystemLoader(searchpath=params._TEMPLATE_PATH)
    tmplEnv = j2.Environment(loader=tmplLoader, trim_blocks=True,
            lstrip_blocks=True)
    tmplEnv.filters['markdown'] = md2ht

    images = build_img_inventory(epubdir, imgdir, epub_meta['opf'][1])

    # generate metadata files:
    uuid = gen_uuid(meta.__str__() + dt.utcnow().__str__())
    for tmpl_file, out_file in epub_meta.values():
        render_output(tmplEnv, tmpl_file, pages=pages,
                images=images, uuid=uuid,
                out_file=os.path.join(epubdir, out_file), **meta)

    # now content:
    kwargs = {'meta': meta, 'epubdir': epubdir, 'srcdir': srcdir,
             'htmldir': htmldir, 'tmpl_env': tmplEnv,
             'yaml_incl_dir': yaml_incl_dir, 'dropcaps': dropcaps}

    def gen_content(pages, **kwargs):
        for pg in pages:
            if pg['type'] == 'chapter':
                gen_chapter(pg, **kwargs)
            elif pg['type'] == 'static':
                cp_static(pg, **kwargs)
            elif pg['type'] == 'template':
                gen_from_tmpl(pg, pages, **kwargs)
            if 'children' in pg:
                gen_content(pg['children'], **kwargs)

    gen_content(pages, **kwargs)

    return None
