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
from markdown import markdown

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
                   'svg': 'svg'}

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
    src_dir = pg.get('srcdir')
    src_path = os.path.join(epubdir, src_dir if src_dir else
                            srcdir)
    src_path = os.path.abspath(src_path)
    md_base = pg.get('src', pg['id'])
    mdfile = os.path.join(src_path, md_base + '.md')
    outfile = os.path.join(epubdir, htmldir, pg['id'] +
                           '.xhtml')
    par_style = pg.get('parstyle', params._BASIC_CH_PAR_STYLE)
    logging.info('generating %s from %s with par style "%s"...', outfile,
            mdfile, par_style)
    with open(mdfile, 'r') as foi:
        ht_text = markdown(foi.read(), extensions=['smarty'])
    # styling for in-page section breaks:
    for pat in break_re:
        pat = r'<p>\s*(?P<first>{})\s*</p>'.format(pat)
        ht_text = re.sub(
                pat, '<p class="{}">\g<first></p>'.format(
                params._IN_PG_SEC_BREAK_STYLE), ht_text)
    ht_text = re.sub(r'<p>', r'<p class="{}">'.format(par_style), ht_text)
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
    tmpl_name = pg.get('template', 'chapter')
    ht_text = render_output(tmpl_env, tmpl_name, chapter_content=ht_text,
            header_title=meta['title'] + ' | ' + pg['heading'], pg_meta=pg)
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
    # `beg_raw`, `end_raw` and `pars` need to be run through markdown:
    for raw in ['beg_raw', 'end_raw']:
        if raw not in pg:
            continue
        pg[raw] = markdown(pg[raw], extensions=['smarty'])
    if 'pars' in pg:
        pg['pars'] = [markdown(p, extensions=['smarty']).replace(
                '<p>', '').replace('</p>', '')
                      for p in pg['pars']]
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
    with open(os.path.join(epubdir, mmyaml), 'r') as foi:
        mainmatter = yaml.load(foi)
    fm = meta.get('frontmatter', [])
    bm = meta.get('backmatter', [])
    pages = (fm if fm else []) + mainmatter + (bm if bm else [])

    tmplLoader = j2.FileSystemLoader(searchpath=params._TEMPLATE_PATH)
    tmplEnv = j2.Environment(loader=tmplLoader, trim_blocks=True)

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
