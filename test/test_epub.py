import unittest
from unittest.mock import patch
from io import StringIO
import sys
import logging

from ipub import epub
from ipub import params


logging.basicConfig(level=logging.INFO)


class InitTest(unittest.TestCase):

    @patch('ipub.epub.utils.run_script', return_value=(
            b'this should print as info', b'this should print as error'))
    def test_init(self, run_script_mock):
        target = 'target_dir'
        call_args = ('cp', '-ar', params._EPUB_SKELETON_PATH, target)
        epub.init(target)
        self.assertEqual(run_script_mock.call_args[0], call_args)
