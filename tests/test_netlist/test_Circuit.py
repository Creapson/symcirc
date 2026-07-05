import unittest
from netlist.Circuit import Circuit

class TestCircuit(unittest.TestCase):

    # this is the __init__ function
    def setUp(self):
        self.circuit = Circuit(name="TestBench")

    # All functions from Circuit
    def test_set_name(self):
        self.circuit.set_name("TestCircuit")
        self.assertEqual(self.circuit.name, "TestCircuit")

    """
    def test_add_param(self):
        pass

    def test_resolve_controlled_sources(self):
        pass

    def test_get_sweep(self):
        pass

    def test_set_netlist_path(self):
        pass

    def test_set_separator(self):
        pass

    def test_set_bipolar_model(self):
        pass

    def test_set_mosfet_model(self):
        pass

    def test_update_nodes(self):
        pass

    def test_get_nodes(self):
        pass

    def test_get_elements(self):
        pass

    def test_get_element(self):
        pass

    def test_get_subcircuits(self):
        pass

    def test_get_models(self):
        pass

    def test_add_node(self):
        pass

    def test_add_model(self):
        pass

    def test_add_element(self):
        pass

    def test_add_subcircuit(self):
        pass

    def test_flatten_subcircuit(self):
        pass

    def test_flatten(self):
        pass

    def test_remove_unused_models(self):
        pass

    def test_to_ai_string(self):
        pass

    """
