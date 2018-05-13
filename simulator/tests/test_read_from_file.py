import unittest
import sys, os

sys.path.insert(0, os.path.abspath('.'))

from libs import cmds_from_file as cff


class TestReadFromFile(unittest.TestCase):

    def test_read_test_file(self):
        node_infos = cff.read_file("./infos/cmds_test.txt")
        assert (len(node_infos) == 2)
        assert ('h2' in node_infos)
        assert ('h1' in node_infos)

