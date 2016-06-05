import unittest
import re
from urllib.parse import urlparse, parse_qsl, unquote_plus

from ipub import utils


# from http://stackoverflow.com/a/9468284
class Url(object):
    '''A url object that can be compared with other url orbjects
    without regard to the vagaries of encoding, escaping, and ordering
    of parameters in query strings.'''

    def __init__(self, url):
        parts = urlparse(url)
        _query = frozenset(parse_qsl(parts.query))
        _path = unquote_plus(parts.path)
        parts = parts._replace(query=_query, path=_path)
        self.parts = parts

    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)


class Num2EngTest(unittest.TestCase):

    def test_numbers(self):
        self.assertEqual(utils.num2eng(0), 'zero')
        self.assertEqual(utils.num2eng(2), 'two')
        self.assertEqual(utils.num2eng(21), 'twenty one')
        self.assertEqual(utils.num2eng(110), 'one hundred ten')
        self.assertEqual(utils.num2eng(1461), 'one thousand, four hundred '
                         'sixty one')

class UrlQueryTest(unittest.TestCase):

    def test_mk_query_urls(self):
        # set up test data:
        in_urls = ['https://www.github.com/ms8r/scriv2epub',
                   'https://github.com/ms8r/scriv2epub/blob/master/README.md'
                   '?utm_campaign=generic&some_parameter=some_value',
                   'https://github.com/wcember/pypub']
        ht_in = """<p>You can read more about this project on
            <a href="{}">GitHub</a> where you can look at the
            <href="{}">README</a> file. A related repo on GitHub is @wcember's
            <a href="{}">PyPub</a> on GitHub.</p>""".format(*in_urls)
        query_url_re = '"(https://(?:www.)?github.com/ms8r[^"]*)"'
        qmap = {
            'utm_campaign': 'url_query_test',
            'utm_medium': 'a_python_script',
            'utm_source': 'the_same_script'
        }
        expected_out = [
                'https://www.github.com/ms8r/scriv2epub'
                '?utm_medium=a_python_script&amp;utm_campaign=url_query_test'
                '&amp;utm_source=the_same_script',
                'https://github.com/ms8r/scriv2epub/blob/master/README.md'
                '?utm_medium=a_python_script&amp;utm_source=the_same_script'
                '&amp;utm_campaign=url_query_test'
                '&amp;some_parameter=some_value',
                'https://github.com/wcember/pypub']

        ht_out = utils.mk_query_urls(ht_in, query_url_re, qmap)
        generic_url_re = '"(http(?:s)?://[^"]*)"'
        out_urls = re.findall(generic_url_re, ht_out)
        self.assertEqual(len(expected_out), len(out_urls))
        for actual, expected in zip(out_urls, expected_out):
            self.assertEqual(Url(actual), Url(expected))


class RunScriptTest(unittest.TestCase):

    def test_run_script_std(self):
        self.assertEqual(utils.run_script('date', '-u',
                '-d 2016-04-08T11:19:04+00:00' , '+%Y-%m-%d'),
                (b'2016-04-08\n', None))

    @unittest.skip('not implemented yet')
    def test_run_script_err(self):
        self.assertEqual(utils.run_script(''), '')

if __name__ == '__main__':
    unittest.main()
