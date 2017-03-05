import math
import re
import subprocess
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl
import logging
from cookiecutter.main import cookiecutter

def cc_create(tmpl, extra_context=None, output_dir='.', no_input=False):
    """
    Create new book project from cookiecutter template.
    """
    if extra_context is None:
        extra_context = {}

    cookiecutter(tmpl,  no_input=no_input, extra_context=extra_context,
            output_dir=output_dir)


def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def run_script(*args):
    """
    Runs external executable with list of arguments in `args`.

    Returns a tuple (stdout, stderr) with script output.
    """
    logging.debug('calling Popen with args: %s', ' '.join(args))
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()


def mk_query_urls(ht_text, url_re, qmap):
    """
    Appends a URL query string contructed from `qmap` to all URLs that match
    `url_re` in `ht_text`. If the original URL already contained one of the
    query elements in `qmap` this will be overwritten with the `qmap` version.
    Returns the text with substitutions made.
    """
    links = re.findall(url_re, ht_text)
    for ll in set(links):
        old = urlsplit(ll)
        if old.query:
            updated_qmap = dict(parse_qsl(old.query) + list(qmap.items()))
        else:
            updated_qmap = qmap
        new = list(old[:3]) + [urlencode(updated_qmap)] + list(old[-1:])
        ht_text = ht_text.replace('"{}"'.format(ll),
                '"{}"'.format(urlunsplit(new).replace('&', '&amp;')))
    return ht_text



"""Convert number to English words

Adapted from Miki Tebeka's blog [1] to work with Python 3 and to strip trailing
spaces.

Algorithm from http://mini.net/tcl/591

[1] http://www.blog.pythonlibrary.org/2012/06/02/how-to-convert-decimal-numbers-to-words-with-python/
    email: tebeka@cs.bgu.ac.il
"""

# Tokens from 1000 and up
_PRONOUNCE = [
    'vigintillion',
    'novemdecillion',
    'octodecillion',
    'septendecillion',
    'sexdecillion',
    'quindecillion',
    'quattuordecillion',
    'tredecillion',
    'duodecillion',
    'undecillion',
    'decillion',
    'nonillion',
    'octillion',
    'septillion',
    'sextillion',
    'quintillion',
    'quadrillion',
    'trillion',
    'billion',
    'million',
    'thousand',
    ''
]

# Tokens up to 90
_SMALL = {
    '0' : '',
    '1' : 'one',
    '2' : 'two',
    '3' : 'three',
    '4' : 'four',
    '5' : 'five',
    '6' : 'six',
    '7' : 'seven',
    '8' : 'eight',
    '9' : 'nine',
    '10' : 'ten',
    '11' : 'eleven',
    '12' : 'twelve',
    '13' : 'thirteen',
    '14' : 'fourteen',
    '15' : 'fifteen',
    '16' : 'sixteen',
    '17' : 'seventeen',
    '18' : 'eighteen',
    '19' : 'nineteen',
    '20' : 'twenty',
    '30' : 'thirty',
    '40' : 'forty',
    '50' : 'fifty',
    '60' : 'sixty',
    '70' : 'seventy',
    '80' : 'eighty',
    '90' : 'ninety'
}

def _get_num(num):
    '''Get token <= 90, return '' if not matched'''
    return _SMALL.get(num, '')

def _triplets(l):
    '''Split list to triplets. Pad last one with '' if needed'''
    res = []
    for i in range(int(math.ceil(len(l) / 3.0))):
        sect = l[i * 3 : (i + 1) * 3]
        if len(sect) < 3: # Pad last section
            sect += [''] * (3 - len(sect))
        res.append(sect)
    return res

def _norm_num(num):
    """Normelize number (remove 0's prefix). Return number and string"""
    n = int(num)
    return n, str(n)

def _small2eng(num):
    '''English representation of a number <= 999'''
    n, num = _norm_num(num)
    hundred = ''
    ten = ''
    if len(num) == 3: # Got hundreds
        hundred = _get_num(num[0]) + ' hundred'
        num = num[1:]
        n, num = _norm_num(num)
    if (n > 20) and (n % 10 > 0): # Got ones
        tens = _get_num(num[0] + '0')
        ones = _get_num(num[1])
        ten = tens + ' ' + ones
    else:
        ten = _get_num(num)
    if hundred and ten:
        return hundred + ' ' + ten
        #return hundred + ' and ' + ten
    else: # One of the below is empty
        return hundred + ten

def num2eng(num):
    '''English representation of a number'''
    num = str(num) # Convert to string, throw if bad number
    if (len(num) // 3 >= len(_PRONOUNCE)): # Sanity check
        raise ValueError('Number too big')

    if num == '0': # Zero is a special case
        return 'zero'

    # Create reversed list
    x = list(num)
    x.reverse()
    pron = [] # Result accumolator
    ct = len(_PRONOUNCE) - 1 # Current index
    for a, b, c in _triplets(x): # Work on triplets
        p = _small2eng(c + b + a)
        if p:
            pron.append(p + ' ' + _PRONOUNCE[ct])
        ct -= 1
    # Create result
    pron.reverse()
    return (', '.join(pron)).strip()

