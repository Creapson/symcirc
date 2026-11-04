r"""Export a Sparse Tableau matrix of a circuit to CSV.

Dumps the symbolic T matrix with row/column labels attached, plus the RHS,
so it can be diffed cell-by-cell against an Analog Insydes matrix export
without having to read numbers off a screenshot.

Analog Insydes' own SparseTableau.m is loop based (KVL over a spanning
tree, no separate node-potential unknowns) - that is what
Sparse_Tableau_Normal.py implements, and it is confirmed to match Insydes'
output row for row, sign for sign. Sparse_Tableau_Extended.py is a
different (also correct) formulation that adds node potentials as
unknowns; its matrix will not line up cell-by-cell with Insydes even when
both are right. Default here is "normal" for that reason.

Usage (run from the project root):
    python analysis_methoden\export_tableau_matrix.py path\to\circuit.cir
    python analysis_methoden\export_tableau_matrix.py path\to\circuit.cir --method extended
    python analysis_methoden\export_tableau_matrix.py path\to\circuit.cir --bipolar-model BJT_BasicModel
    python analysis_methoden\export_tableau_matrix.py path\to\circuit.cir --out path\to\circuit.out --output matrix.csv
    python analysis_methoden\export_tableau_matrix.py path\to\circuit.cir --numeric

Equivalently as a module:
    python -m analysis_methoden.export_tableau_matrix path\to\circuit.cir
"""

import argparse
import csv
import os
import sys

# Running this file directly puts analysis_methoden/ on sys.path instead of the
# project root, so the project's packages would not be importable. Adding the
# root here keeps both "python analysis_methoden/export_tableau_matrix.py" and
# "python -m analysis_methoden.export_tableau_matrix" working.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis_methoden.insydes_naming as ins
from parser.NetlistParser import get_circuit_from_file
from analysis_methoden.Analysis_Factory import create_analysis
from analysis_methoden.Sparse_Tableau_Normal import SparseTableauNormal


def build_row_labels(sta):
    if isinstance(sta, SparseTableauNormal):
        # row order: [ loop (KVL, one per link branch) | KCL (one per node) |
        #              element eqs (one per branch, original order) ]
        inv_node_map = {index: name for name, index in sta.node_map.items() if index != 0}
        loop_labels = [f"KVL_{sta.branches[j].symbol}" for j in sta.links]
        kcl_labels = [f"KCL_{inv_node_map[index]}" for index in range(1, sta.n + 1)]
        eleq_labels = [f"I_{branch.symbol}" for branch in sta.branches]
        return loop_labels + kcl_labels + eleq_labels

    # SparseTableau (Extended): [ branch voltage def | KCL | element eqs ]
    inv_node_map = {index: name for name, index in sta.node_map.items() if index != 0}
    udef_labels = [f"U_{branch.symbol}" for branch in sta.branches]
    kcl_labels = [f"KCL_{inv_node_map[index]}" for index in range(1, sta.n + 1)]
    eleq_labels = [f"I_{branch.symbol}" for branch in sta.branches]
    return udef_labels + kcl_labels + eleq_labels


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cir_path", help="path to the .cir netlist")
    parser.add_argument("--method", choices=["normal", "extended"], default="normal",
                         help="'normal' = loop based, matches Analog Insydes' "
                              "SparseTableau.m (default). 'extended' = node "
                              "potential based, a different but also correct "
                              "formulation that will NOT line up cell-by-cell "
                              "with Insydes.")
    parser.add_argument("--out", dest="out_path", default="",
                         help="path to the PSpice .out file with small-signal "
                              "BJT/MOSFET params (defaults to <cir_path> with .out extension)")
    parser.add_argument("--bipolar-model", default="BJT_BasicModel",
                         help="small signal BJT model name from "
                              "library/small_signal_models/bipolar_models (default: BJT_BasicModel)")
    parser.add_argument("--separator", default=None,
                         help="element name separator used when flattening subcircuits/models")
    parser.add_argument("--output", default="",
                         help="output CSV path (default: <cir_path>_matrix.csv next to the netlist)")
    parser.add_argument("--numeric", action="store_true",
                         help="substitute element values instead of keeping symbols")
    parser.add_argument("--naming", choices=["plain", "insydes"], default="plain",
                         help="'insydes' relabels everything the way Analog "
                              "Insydes prints it (V_RPI_Q1, gm_Q1, CS_VCS_Q1) "
                              "so the CSV can be diffed against an Insydes "
                              "export directly")
    args = parser.parse_args()

    cir_path = os.path.abspath(args.cir_path)
    out_path = os.path.abspath(args.out_path) if args.out_path else os.path.splitext(cir_path)[0] + ".out"
    output_path = args.output or os.path.splitext(cir_path)[0] + "_matrix.csv"

    circuit = get_circuit_from_file(cir_path)
    circuit.set_bipolar_model(args.bipolar_model)
    if args.separator:
        circuit.set_separator(args.separator)

    flatten_kwargs = {"flatten_models": True}
    if os.path.exists(out_path):
        flatten_kwargs["out_file_path"] = out_path
    else:
        print(f"Warning: no .out file at {out_path}, BJT/MOSFET params stay symbolic.")
    circuit.flatten(**flatten_kwargs)

    sta = create_analysis(circuit, method="SparseTableau" if args.method == "normal" else "ExtendedTableau")
    sta.buildEquationsSystem()

    T = sta.T
    if args.numeric:
        T = T.subs(sta.value_dict)

    rhs = sta.RHS

    if args.naming == "insydes":
        col_labels = ins.unknown_labels(sta)
        row_labels = ins.row_labels(sta)
        mapping = {} if args.numeric else ins.symbol_map(sta)
    else:
        col_labels = sta.get_unknowns_as_strings()
        row_labels = build_row_labels(sta)
        mapping = {}

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["row \\ col"] + col_labels + ["RHS"])
        for i, row_label in enumerate(row_labels):
            row_values = [ins.render(T[i, j], mapping) for j in range(T.cols)]
            writer.writerow([row_label] + row_values + [ins.render(rhs[i], mapping)])

    print(f"Method: {args.method}")
    print(f"Elements after flatten: {len(circuit.elements)}")
    print(f"Matrix shape: {T.shape}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
