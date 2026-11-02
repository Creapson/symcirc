import unittest

from parser.ltspice.LtspiceParser import LtspiceParser
from parser.NetlistParser import get_circuit_from_file, detect_netlist_format

LTSPICE_NET = "test_circuits/simple_lc_ltspice.net"
PSPICE_NET = "test_circuits/simple_lc.net"


class TestLtspiceParser(unittest.TestCase):

    def setUp(self):
        self.circuit = LtspiceParser(LTSPICE_NET)._parse()

    def test_parses_all_elements(self):
        names = sorted(el.name for el in self.circuit.get_elements())
        self.assertEqual(names, ["C1", "L1", "R3", "V1"])

    def test_ref_des_not_mangled(self):
        # Plain LTspice ref-des (e.g. "R3") must survive remove_type_prefix()
        # unchanged - it should only strip the MicroSim "TYPE_REFDES" duplication.
        r3 = self.circuit.get_element("R3")
        self.assertIsNotNone(r3)
        self.assertEqual(r3.type, "R")
        self.assertEqual(r3.connections, ["3", "0"])
        self.assertEqual(r3.params["value_dc"], "10")

    def test_source_dc_and_ac_values(self):
        v1 = self.circuit.get_element("V1")
        self.assertEqual(v1.connections, ["1", "0"])
        self.assertEqual(v1.params["value_dc"], "0")
        self.assertEqual(v1.params["value_ac"], "1")

    def test_sweep_parsed(self):
        self.assertEqual(self.circuit.params["sweep"], "DEC 101 0.1 10000000.0")

    def test_matches_equivalent_pspice_circuit(self):
        # Same topology/values as test_circuits/simple_lc.net (PSpice dialect),
        # just with LTspice-style ref-des and syntax - parsing both should
        # produce circuits with the same nodes and per-type element values.
        pspice_circuit = get_circuit_from_file(PSPICE_NET)

        self.assertEqual(sorted(self.circuit.get_nodes()), sorted(pspice_circuit.get_nodes()))

        def value_by_type(circuit):
            return sorted(
                (el.type, el.params.get("value_dc", el.params.get("value_ac")))
                for el in circuit.get_elements()
            )

        self.assertEqual(value_by_type(self.circuit), value_by_type(pspice_circuit))


class TestLtspiceParserAdvanced(unittest.TestCase):
    """Regression tests for gaps found reviewing real LTspice-exported files:
    a 4-node BJT statement, .lib-resolved models, and "+"-continuation lines
    feeding a source's DC/AC token walk.
    """

    def test_bjt_substrate_node_is_dropped(self):
        # LTspice always writes an explicit substrate/bulk node for BJTs
        # ("Q1 C B E S model"); library/small_signal_models/bipolar_models
        # only models 3 terminals (C, B, E), so the 4th node must not be
        # passed through as a bogus connection.
        circuit = LtspiceParser("test_circuits/ltspice_bjt.net")._parse()
        q1 = circuit.get_element("Q1")
        self.assertIsNotNone(q1)
        self.assertEqual(q1.connections, ["3", "2", "0"])
        self.assertEqual(q1.params["ref_model"], "BC547B")

    def test_lib_model_is_resolved(self):
        # BC547B is only defined in the .lib fixture, not inline in the .net.
        circuit = LtspiceParser("test_circuits/ltspice_bjt.net")._parse()
        self.assertIn("BC547B", circuit.get_models())
        self.assertEqual(circuit.get_models()["BC547B"].type, "NPN")

    def test_ac_magnitude_is_not_glued_to_its_phase(self):
        # LTspice exports AC sources as "AC <magnitude> <phase>". Concatenating
        # both tokens (what SpiceParser's token walk does) turned "AC 1 0" into
        # a magnitude of "10" - a silent factor-of-ten error in every AC
        # analysis of an LTspice circuit.
        circuit = LtspiceParser("test_circuits/ltspice_ac_phase.net")._parse()
        vin = circuit.get_element("Vin")
        self.assertIsNotNone(vin)
        self.assertEqual(vin.params["value_ac"], "1")
        self.assertEqual(vin.params["value_ac_phase"], "0")

    def test_continuation_line_feeds_source_token_walk(self):
        # "+ AC 1" on its own continuation line must still be visible to the
        # DC/AC token walk once merged - this needs Line.append() to keep
        # .tokens in sync, not just ._text.
        circuit = LtspiceParser("test_circuits/ltspice_continuation.net")._parse()
        v1 = circuit.get_element("V1")
        self.assertEqual(v1.params["value_dc"], "0")
        self.assertEqual(v1.params["value_ac"], "1")


class TestFormatDetection(unittest.TestCase):

    def test_detects_ltspice(self):
        self.assertEqual(detect_netlist_format(LTSPICE_NET), "ltspice")

    def test_detects_pspice(self):
        self.assertEqual(detect_netlist_format(PSPICE_NET), "pspice")

    def test_get_circuit_from_file_dispatches_ltspice(self):
        circuit = get_circuit_from_file(LTSPICE_NET)
        self.assertEqual(sorted(el.name for el in circuit.get_elements()), ["C1", "L1", "R3", "V1"])


if __name__ == "__main__":
    unittest.main()
