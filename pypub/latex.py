"""
Functions for generating LaTeX output from mainmatter Markdown source files.
"""

import re
import os.path
import logging
import yaml
import jinja2 as j2

from . import params


def fleuronize(s, symbol=r'\\infty', rpt=3, math=True):
    """
    Replaces instances of ***, ###, and <<<>>> in string `s` (also if backslash
    escaped and/or spearated by spaces) with raw LaTeX code for a fleuron,
    using `rpt` repetitions of character `symbol` (can be a LaTeX command in
    which case the leading \ must be escaped as \\). If `math` is `True`
    `symbol` will be placed in math environment.
    """
    patterns = [
            r'\\?[*]\s*\\?[*]\s*\\?[*]',
            r'\\?[#]\s*\\?[#]\s*\\?[#]',
            r'\\?[<]\s*\\?[<]\s*\\?[<]\s*\\?[>]\s*\\?[>]\s*\\?[>]',
    ]
    repl = symbol * rpt
    if math:
        repl = '$' + repl + '$'
    repl = r'\\plainbreak{{1}}\\fancybreak{{{}}}\\plainbreak{{1}}'.format(repl)

    for pat in patterns:
        s = re.sub(pat, repl, s)

    return s


def mm_gen(mm, src_dir, hoffs):
    """
    Generator that yields the chapters in mm (mainmatter list of dicts) with
    headings at correct level (top level will be equal to `hoffs` + 1).
    Source markdown files are assumed to reside in `src_dir`.
    """
    level = hoffs + 1
    for m in mm:
        s = '{}{}\n\n'.format('#' * (level), m['heading'])
        # *** for now chapters only ***
        if not m['type'] == 'chapter':
            continue
        with open(os.path.join(src_dir, m['id'] + '.md'), 'r') as foi:
            s += foi.read()
        yield s
        if 'children' in m:
            yield from mm_gen(m['children'], src_dir, level)


def mmcat(mmyaml, outfile, mddir, hoffset=0, lbreak=False):
    """
    Concatenates all mainmatter markdown sources with headings at correct level
    inserted.
    """
    with open(mmyaml, 'r') as foi:
        mainmatter = yaml.load(foi)

    foo = outfile if args.outfile else sys.stdout
    for m in mm_gen(mainmatter, mddir, hoffset):
        if lbreak:
            m = fleuronize(m)
        foo.write('{}\n\n'.format(m))

    foo.close()


def mkbook(metayaml, book, tmpl):
    """
    Generates LaTeX for a print book, given meta YAML, mainmatter md and a
    template.
    """
    with open(args.metayaml, 'r') as foi:
        meta = yaml.load(foi)

    tmplLoader = j2.FileSystemLoader(searchpath=params._TEMPLATE_PATH)
    tmplEnv = j2.Environment(
            loader=tmplLoader,
            trim_blocks=True,
            block_start_string='<%',
            block_end_string='%>',
            variable_start_string='<&',
            variable_end_string='&>',
            comment_start_string='<#',
            comment_end_string='#>')

    # generate main document file:
    logging.info('generating main file %s from template %s...',
            args.book + '.tex', args.tmpl + params._TEMPLATE_EXT)
    tmpl = tmplEnv.get_template(args.tmpl + params._TEMPLATE_EXT)
    with open(args.book + '.tex', 'w') as foo:
        foo.write(tmpl.render(meta))

    # generate any dynamic front or backmatter files:
    fm = meta.get('frontmatter', [])
    bm = meta.get('backmatter', [])
    pages = (fm if fm else []) + (bm if bm else [])
    pages = [p for p in pages if p['type'] == 'template']
    for pg in pages:
        logging.info('generating page for "%s" from template %s...',
                pg['heading'], pg['template'] + params._TEMPLATE_EXT)
        tmpl_name = pg.get('template')
        if not tmpl_name:
            tmpl_name = pg['id']
        pg_data = meta.get(pg['id'])
        # TODO: encapsulate finding the right page_data yaml so it can be used
        # for epub as well as for print
        if not pg_data:
            # look for supplementary YAML file with page data,
            # first in current dir, then in yincl:
            try:
                with open(pg['id'] + '.yaml', 'r') as foi:
                    pg_data = yaml.load(foi)
            except FileNotFoundError as e:
                logging.warning(e)
            try:
                with open(os.path.join(args.yincl, pg['id'] +
                          '.yaml'), 'r') as foi:
                    pg_data = yaml.load(foi)
            except FileNotFoundError as e:
                logging.warning(e)
        tmpl = tmplEnv.get_template(tmpl_name + params._TEMPLATE_EXT)
        outfile = os.path.join(pg['id'] + '.tex')
        logging.info('generating %s...', outfile)
        with open(outfile, 'w') as foo:
            foo.write(tmpl.render(meta, pg_meta=pg, pg_data=pg_data))


