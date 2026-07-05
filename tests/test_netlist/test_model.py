import unittest
from netlist.Model import Model

class TestCircuit(unittest.TestCase):

    def setUp(self):
        """Initializes a fresh Circuit instance before every test."""
        self.model = Model(name="TestBench")

    def test_add_param(self):
        self.model.add_param("test_param", 42)
        self.assertEqual(self.model.params.get("test_param"), 42)

    """
    def test_get_generated_subcircuit(self):
        pass
    """
