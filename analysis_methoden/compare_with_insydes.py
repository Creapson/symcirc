r"""Diff our Sparse Tableau matrix against one exported from Analog Insydes.

Insydes side, in Mathematica:

    eqs  = CircuitEquations[netlist, Formulation -> SparseTableau];
    eqns = eqs[[1]];
    vars = eqs[[2]];
    {c0, c1} = CoefficientArrays[eqns, vars];
    dir = "C:\\Users\\aokum\\Desktop\\";
    str[e_] := ToString[InputForm[e]];
    Export[dir <> "ai_A.csv",   Map[str, Normal[c1], {2}],      "CSV"];
    Export[dir <> "ai_x.csv",   List /@ Map[str, vars],          "CSV"];
    Export[dir <> "ai_rhs.csv", List /@ Map[str, -Normal[c0]],   "CSV"];

Our side (run from the project root):

    python analysis_methoden\export_tableau_matrix.py <circuit>.cir --separator _ --naming insydes

Then:

    python analysis_methoden\compare_with_insydes.py <circuit>_matrix.csv ai_A.csv ai_x.csv
        [--rhs ai_rhs.csv]

Columns are matched by unknown name, so a different column order is not
reported as a difference. Rows are matched by content, because Insydes' A has
no row labels and a tableau is only defined up to the order of its KVL and KCL
equations: any row of ours that has an identical counterpart on the other side
is fine, whatever position it sits in. What is left over on either side is the
real difference.
"""

import argparse
import csv
import re

import sympy as sp

# Mathematica writes 2.48*^3 where Python writes 2.48e3
MATHEMATICA_EXPONENT = re.compile(r"\*\^")


def normalise_name(name):
    """Bring an Insydes symbol and one of ours to the same spelling."""
    return name.strip().strip('"').replace("$", "_").upper()


def parse_cell(text):
    """Turn one exported cell into a sympy expression."""
    text = text.strip().strip('"')
    if not text:
        return sp.Integer(0)

    text = MATHEMATICA_EXPONENT.sub("e", text)
    text = text.replace("$", "_")

    try:
        return sp.sympify(text)
    except (sp.SympifyError, SyntaxError, TypeError):
        return sp.Symbol(text)


def read_our_matrix(path):
    """Read the CSV written by export_tableau_matrix.py --naming insydes."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    header = rows[0]
    has_rhs = header[-1].strip().upper() == "RHS"
    columns = [normalise_name(name) for name in header[1:-1 if has_rhs else None]]

    labels, matrix, rhs = [], [], []
    for row in rows[1:]:
        labels.append(row[0])
        values = row[1:-1] if has_rhs else row[1:]
        matrix.append([parse_cell(cell) for cell in values])
        rhs.append(parse_cell(row[-1]) if has_rhs else sp.Integer(0))

    return labels, columns, matrix, rhs


def read_insydes_matrix(matrix_path, unknowns_path, rhs_path=""):
    """Read the three CSVs exported from Mathematica."""
    with open(matrix_path, newline="", encoding="utf-8") as handle:
        matrix = [[parse_cell(cell) for cell in row]
                  for row in csv.reader(handle) if row]

    with open(unknowns_path, newline="", encoding="utf-8") as handle:
        columns = [normalise_name(row[0]) for row in csv.reader(handle) if row]

    rhs = [sp.Integer(0)] * len(matrix)
    if rhs_path:
        with open(rhs_path, newline="", encoding="utf-8") as handle:
            rhs = [parse_cell(row[0]) for row in csv.reader(handle) if row]

    return columns, matrix, rhs


def row_key(row, rhs_value):
    """A hashable, order independent fingerprint of one equation.

    sympy expressions are compared after expand() so that gm*u and u*gm, or
    -(a - b) and b - a, count as the same coefficient.
    """
    return (tuple(sp.srepr(sp.expand(value)) for value in row),
            sp.srepr(sp.expand(rhs_value)))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("our_csv", help="CSV from export_tableau_matrix.py")
    parser.add_argument("insydes_matrix", help="ai_A.csv")
    parser.add_argument("insydes_unknowns", help="ai_x.csv")
    parser.add_argument("--rhs", default="", help="ai_rhs.csv, optional")
    args = parser.parse_args()

    our_labels, our_columns, our_matrix, our_rhs = read_our_matrix(args.our_csv)
    their_columns, their_matrix, their_rhs = read_insydes_matrix(
        args.insydes_matrix, args.insydes_unknowns, args.rhs)

    print(f"ours    : {len(our_matrix)} x {len(our_columns)}")
    print(f"insydes : {len(their_matrix)} x {len(their_columns)}")
    print()

    only_ours = [name for name in our_columns if name not in set(their_columns)]
    only_theirs = [name for name in their_columns if name not in set(our_columns)]
    if only_ours or only_theirs:
        print("unknowns do not line up, so the cells cannot be compared:")
        if only_ours:
            print(f"  only in ours    : {', '.join(only_ours)}")
        if only_theirs:
            print(f"  only in insydes : {', '.join(only_theirs)}")
        print()
        return

    # reorder their columns into our order
    position = {name: index for index, name in enumerate(their_columns)}
    their_matrix = [[row[position[name]] for name in our_columns]
                    for row in their_matrix]

    remaining = {}
    for index, row in enumerate(their_matrix):
        remaining.setdefault(row_key(row, their_rhs[index]), []).append(index)

    unmatched = []
    for index, row in enumerate(our_matrix):
        key = row_key(row, our_rhs[index])
        if remaining.get(key):
            remaining[key].pop()
        else:
            unmatched.append(index)

    leftover = sorted(i for indices in remaining.values() for i in indices)

    if not unmatched and not leftover:
        print("identical: every equation has a counterpart on the other side.")
        return

    print(f"{len(unmatched)} of our rows have no counterpart in Insydes:")
    for index in unmatched:
        terms = " ".join(f"{our_columns[j]}={our_matrix[index][j]}"
                         for j in range(len(our_columns))
                         if our_matrix[index][j] != 0)
        print(f"  row {index + 1:>3}  {our_labels[index]:<16} {terms}"
              f"  | RHS={our_rhs[index]}")

    print()
    print(f"{len(leftover)} Insydes rows have no counterpart in ours:")
    for index in leftover:
        terms = " ".join(f"{our_columns[j]}={their_matrix[index][j]}"
                         for j in range(len(our_columns))
                         if their_matrix[index][j] != 0)
        print(f"  row {index + 1:>3}  {terms}  | RHS={their_rhs[index]}")


if __name__ == "__main__":
    main()
