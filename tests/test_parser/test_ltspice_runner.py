import os
import unittest

from parser.ltspice.LtspiceRunner import build_op_netlist, find_ltspice, generate_op_log

# A real LTspice ".ac" export (Draft6.net), trimmed to the lines that matter.
AC_NETLIST = [
    "* D:\\LtSpice vs PSpice\\LtSpiceBasisschaltung\\Draft6.asc",
    "Vin 1 0 SINE(0 100m 1k) AC 1 0",
    "RS 2 1 600",
    "Q1 4 5 3 0 BC546B",
    ".model NPN NPN",
    ".lib C:\\Users\\x\\AppData\\Local\\LTspice\\lib\\cmp\\standard.bjt",
    "* .op",
    ".ac dec 101 0.1 1.00GHz",
    ".backanno",
    ".end",
]


class TestBuildOpNetlist(unittest.TestCase):

    def setUp(self):
        self.result = build_op_netlist(AC_NETLIST)

    def test_analysis_directive_is_commented_out(self):
        # ".ac" must not stay active - a netlist carries only one simulation
        # command, and it has to be ".op" for the operating point table.
        self.assertIn("* .ac dec 101 0.1 1.00GHz", self.result)
        self.assertNotIn(".ac dec 101 0.1 1.00GHz", self.result)

    def test_op_is_inserted_before_end(self):
        self.assertIn(".op", self.result)
        self.assertEqual(self.result.index(".op"), self.result.index(".end") - 1)

    def test_exactly_one_op_directive(self):
        # The source already carried a commented-out "* .op"; that one stays a
        # comment and must not produce a second active ".op".
        self.assertEqual(self.result.count(".op"), 1)

    def test_elements_models_and_libs_pass_through(self):
        for line in (
            "Vin 1 0 SINE(0 100m 1k) AC 1 0",
            "RS 2 1 600",
            "Q1 4 5 3 0 BC546B",
            ".model NPN NPN",
            ".lib C:\\Users\\x\\AppData\\Local\\LTspice\\lib\\cmp\\standard.bjt",
            ".backanno",
        ):
            self.assertIn(line, self.result)

    def test_step_is_disabled_too(self):
        # A ".step" left in would repeat the .op point once per step value and
        # write one operating-point table per run.
        result = build_op_netlist(["R1 1 0 1k", ".step param x 1 3 1", ".end"])
        self.assertIn("* .step param x 1 3 1", result)

    def test_subcircuit_ends_is_not_mistaken_for_end(self):
        result = build_op_netlist(
            [".subckt amp in out", "R1 in out 1k", ".ends", ".end"]
        )
        self.assertIn(".ends", result)
        # ".op" belongs before ".end", not before ".ends".
        self.assertEqual(result.index(".op"), result.index(".end") - 1)

    def test_op_is_added_when_netlist_has_no_end(self):
        result = build_op_netlist(["R1 1 0 1k"])
        self.assertEqual(result[-2:], [".op", ".end"])


class TestFindLtspice(unittest.TestCase):

    def test_missing_paths_are_skipped(self):
        # An explicit path that doesn't exist must not be returned; the helper
        # falls through to the known install locations / PATH instead.
        found = find_ltspice(extra_paths=[r"C:\definitely\not\here\LTspice.exe"])
        self.assertNotEqual(found, r"C:\definitely\not\here\LTspice.exe")

    def test_existing_extra_path_wins(self):
        # Any real file is accepted, so this test works without LTspice
        # installed - it only checks the lookup order.
        this_file = os.path.abspath(__file__)
        self.assertEqual(find_ltspice(extra_paths=[this_file]), this_file)


class TestGenerateOpLog(unittest.TestCase):

    def test_missing_executable_raises(self):
        with self.assertRaises(FileNotFoundError):
            generate_op_log(
                "test_circuits/ltspice_bjt.net",
                ltspice_exe=r"C:\definitely\not\here\LTspice.exe",
            )

    def test_missing_netlist_raises(self):
        with self.assertRaises(FileNotFoundError):
            generate_op_log(
                "test_circuits/does_not_exist.net",
                ltspice_exe=os.path.abspath(__file__),
            )


if __name__ == "__main__":
    unittest.main()
