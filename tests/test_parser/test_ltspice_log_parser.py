import os
import tempfile
import unittest

from parser.ltspice.LtspiceParser import LtspiceParser
from parser.NetlistParser import get_circuit_from_file
from netlist.Element import Element

# Real LTspice .op logs, captured from actual LTspice 24.0.12 runs (not
# hand-written): a single-BJT circuit and a BJT+MOSFET circuit.
BASISSCHALTUNG_LOG = "test_circuits/basisschaltung_ltspice.log"
DRAFT5_LOG = "test_circuits/draft5_ltspice.log"


class TestLtspiceLogParser(unittest.TestCase):
    """Tests for LtspiceParser.parse_element_params, the ".log" counterpart
    of SpiceParser.parse_element_params (which reads PSpice's ".out").
    """

    def test_bjt_block_written_to_element(self):
        q1 = Element(name="Q1", historical_name="Q1", type="Q")
        LtspiceParser().parse_element_params(BASISSCHALTUNG_LOG, [q1])

        self.assertEqual(q1.params["Model"], "bc547b")
        self.assertAlmostEqual(float(q1.params["Gm"]), 3.47e-02)
        self.assertAlmostEqual(float(q1.params["Rpi"]), 8.39e03)
        self.assertAlmostEqual(float(q1.params["Ro"]), 7.00e04)
        self.assertAlmostEqual(float(q1.params["Cbe"]), 5.94e-11)
        self.assertAlmostEqual(float(q1.params["Cbc"]), 1.32e-12)
        self.assertAlmostEqual(float(q1.params["Cbx"]), 8.13e-13)

    def test_name_matching_is_case_insensitive(self):
        # netlist keeps "Q1", .log always lowercases the ref-des to "q1"
        q1 = Element(name="Q1", historical_name="Q1", type="Q")
        LtspiceParser().parse_element_params(BASISSCHALTUNG_LOG, [q1])
        self.assertIn("Gm", q1.params)

    def test_preamble_lines_are_not_parsed_as_params(self):
        q1 = Element(name="Q1", historical_name="Q1", type="Q")
        LtspiceParser().parse_element_params(BASISSCHALTUNG_LOG, [q1])
        # "Circuit:", "Start Time:", "Warning: ..." precede the first "Name:"
        # line and must be skipped, not misread as parameters.
        self.assertNotIn("Circuit", q1.params)
        self.assertNotIn("Start", q1.params)
        self.assertNotIn("Warning", q1.params)

    def test_unmatched_element_name_does_not_crash(self):
        # No "Q1" in the elements list - the log's "q1" block should be
        # skipped without raising, with feedback noting the miss.
        other = Element(name="R1", historical_name="R1", type="R")
        parser = LtspiceParser()
        parser.parse_element_params(BASISSCHALTUNG_LOG, [other])
        self.assertEqual(other.params, {})
        self.assertTrue(any("q1" in msg for msg in parser.feedback))

    def test_multiple_blocks_bjt_and_mosfet_both_parsed(self):
        q1 = Element(name="Q1", historical_name="Q1", type="Q")
        m1 = Element(name="M1", historical_name="M1", type="M")
        LtspiceParser().parse_element_params(DRAFT5_LOG, [q1, m1])

        self.assertEqual(q1.params["Model"], "2n2222")
        self.assertAlmostEqual(float(q1.params["Gm"]), 7.29e-03)

        self.assertEqual(m1.params["Model"], "nmos")
        self.assertAlmostEqual(float(m1.params["Gm"]), 1.39e-04)
        self.assertAlmostEqual(float(m1.params["Cgs"]), 0.0)

    def test_mosfet_gds_zero_does_not_produce_rds(self):
        # Real Draft5.log MOSFET block has Gds = 0.00e+00 - the 1/Gds
        # fallback must not divide by zero.
        m1 = Element(name="M1", historical_name="M1", type="M")
        LtspiceParser().parse_element_params(DRAFT5_LOG, [m1])
        self.assertAlmostEqual(float(m1.params["Gds"]), 0.0)
        self.assertNotIn("Rds", m1.params)

    def test_mosfet_gds_to_rds_conversion_synthetic(self):
        # No real .log sample seen so far has a nonzero Gds, so this block is
        # hand-written (synthetic), just to exercise the 1/Gds -> Rds path.
        synthetic_log = (
            "Semiconductor Device Operating Points:\n"
            "                        --- MOSFET Transistors ---\n"
            "Name:          m1\n"
            "Model:        nmos\n"
            "Gm:          1.00e-03\n"
            "Gds:         2.00e-03\n"
            "Cgs:         1.00e-12\n"
            "\n"
        )
        fd, path = tempfile.mkstemp(suffix=".log")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(synthetic_log)

            m1 = Element(name="M1", historical_name="M1", type="M")
            LtspiceParser().parse_element_params(path, [m1])

            self.assertAlmostEqual(float(m1.params["Rds"]), 500.0)
        finally:
            os.remove(path)

    def test_end_to_end_flatten_fills_real_values(self):
        # Q1 in ltspice_bjt.net matches "q1"/"bc547b" in basisschaltung_ltspice.log.
        circuit = get_circuit_from_file("test_circuits/ltspice_bjt.net")
        circuit.flatten(True, BASISSCHALTUNG_LOG)

        rpi = circuit.get_element("RPI.Q1")
        self.assertIsNotNone(rpi)
        # placeholder "rpi" must be replaced by the real numeric value, not
        # left as the literal template string.
        self.assertNotEqual(rpi.params["value_dc"], "rpi")
        self.assertAlmostEqual(float(rpi.params["value_dc"]), 8.39e03)

    def test_pspice_out_path_is_unaffected(self):
        # Regression: an existing PSpice ".out" caller must still take the
        # get_element_parameters_from_outfile branch, not the new .log one.
        circuit = get_circuit_from_file("test_circuits/Emitteramp_deutsch.net")
        circuit.flatten(True, "test_circuits/Emitteramp_deutsch.out")

        rpi = circuit.get_element("RPI.Q1")
        self.assertIsNotNone(rpi)
        self.assertAlmostEqual(float(rpi.params["value_dc"]), 2480.0)


if __name__ == "__main__":
    unittest.main()
