import unittest
from netlist.Element import Element

class TestCircuit(unittest.TestCase):

    def setUp(self):
        """Initializes a fresh Circuit instance before every test."""
        self.element = Element(name="TestBench")

    def test_set_type(self):
        self.element.set_type("R")
        self.assertEqual(self.element.type, "R")

    """
    def test_remtype_prefix(self):
        pass

    def test_get_normalised_name(self):
        pass

    def test_get_symbol(self):
        pass

    def test_add_param(self):
        pass

    def test_set_connections(self):
        pass

    def test_get_connections(self):
        pass

    def test_remap_values(self):
        pass
    """
