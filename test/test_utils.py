import unittest

from pypub import utils


#-----------------------------------------------------------------------------
# Data for UrlQueryTest:
#-----------------------------------------------------------------------------
_url_query_text_in = \
"""<p>You can read more about this project on <a href="https://github.com/ms8r/scriv2epub">GitHub</a> where you can look at the <href="https://github.com/ms8r/scriv2epub/blob/master/README.md?utm_campaign=generic&some_parameter=some_value">README</a> file. A related repo on GitHub is @wcember's <a href="https://github.com/wcember/pypub">PyPub</a> on GitHub.</p>"""

_url_re = '"(https://(?:www.)?github.com/ms8r[^"]*)"'

_qmap = {
    'utm_campaign': 'url_query_test',
    'utm_medium': 'a_python_script',
    'utm_source': 'the_same_script'
}

_url_query_text_out = \
"""<p>You can read more about this project on <a href="https://github.com/ms8r/scriv2epub?utm_campaign=url_query_test&amp;utm_source=the_same_script&amp;utm_medium=a_python_script">GitHub</a> where you can look at the <href="https://www.github.com/ms8r/scriv2epub/blob/master/README.md?utm_campaign=url_query_test&amp;some_parameter=some_value&amp;utm_medium=a_python_script&amp;utm_source=the_same_script">README</a> file. A related repo on GitHub is @wcember's <a href="https://github.com/wcember/pypub">PyPub</a> on GitHub.</p>"""


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
        self.assertEqual(utils.mk_query_urls(_url_query_text_in, _url_re,
                         _qmap), _url_query_text_out)


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
