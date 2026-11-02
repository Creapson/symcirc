"""Factory for choosing which equation system formulation to build.

Three formulations are available, all sharing the same interface:

    ModifiedNodal    - ModifiedNodalAnalysis, unknowns are node potentials
                       plus the currents of voltage sources.
    ExtendedTableau  - SparseTableau, unknowns are [e | i | u], KVL is
                       written through node potentials (A^T * e - u = 0).
    SparseTableau    - SparseTableauNormal, unknowns are [i | u] only, KVL is
                       written as loop equations (B * u = 0). This is the
                       normal form used in the lecture.

Usage:
    from analysis_methoden.Analysis_Factory import create_analysis

    a = create_analysis(circuit, method="SparseTableau")
    a.buildEquationsSystem()
    a.solve("V_2")

Because all three expose buildEquationsSystem, solve, solveNumerical,
get_unknowns_as_strings and get_System_Inputs, calling code does not need to
know which one it received.
"""

from netlist.Circuit import Circuit
from analysis_methoden.Modified_Node_Analysis import ModifiedNodalAnalysis
from analysis_methoden.Sparse_Tableau_Extended import SparseTableau
from analysis_methoden.Sparse_Tableau_Normal import SparseTableauNormal

# Canonical names shown in the GUI dropdown, in display order.
MODIFIED_NODAL = "ModifiedNodal"
EXTENDED_TABLEAU = "ExtendedTableau"
SPARSE_TABLEAU = "SparseTableau"

# Accepted spellings per method, so small variations do not force the caller
# to remember one exact string.
_ALIASES = {
    MODIFIED_NODAL: {
        "modifiednodal", "mna", "modified_nodal_analysis",
        "modifiednodalanalysis", "modified nodal",
    },
    EXTENDED_TABLEAU: {
        "extendedtableau", "extended", "esta", "extended_sta",
        "extended_sparse_tableau", "sparse_tableau_extended",
        "extended tableau",
    },
    SPARSE_TABLEAU: {
        "sparsetableau", "sta", "normal_sta", "sparse_tableau",
        "sparse_tableau_normal", "sparsetableaunormal", "normal",
        "sparse tableau",
    },
}

_CLASSES = {
    MODIFIED_NODAL: ModifiedNodalAnalysis,
    EXTENDED_TABLEAU: SparseTableau,
    SPARSE_TABLEAU: SparseTableauNormal,
}


def _canonical(method: str) -> str:
    """Map any accepted spelling to one of the three canonical names.

    Args:
        method (str): user supplied method name.

    Returns:
        str: the canonical name.

    Raises:
        ValueError: if the name is not recognised.

    """
    key = method.strip().lower()

    for canonical, aliases in _ALIASES.items():
        if key in aliases:
            return canonical

    raise ValueError(
        f"Unknown method '{method}'. Available methods are: "
        f"{', '.join(available_methods())}."
    )


def create_analysis(circuit: Circuit, method: str = SPARSE_TABLEAU):
    """Build an equation system for the given circuit using the chosen method.

    Args:
        circuit (Circuit): the circuit to analyze. Must be flattened if it
            contains transistors or other subcircuits.
        method (str): "ModifiedNodal", "ExtendedTableau" or "SparseTableau",
            case insensitive, a few common spellings are accepted as well.
            Defaults to the normal sparse tableau.

    Returns:
        ModifiedNodalAnalysis | SparseTableau | SparseTableauNormal: an
        already constructed analysis object. buildEquationsSystem() still has
        to be called, or solve()/solveNumerical() can be used directly since
        both build the system on first use.

    Raises:
        ValueError: if method is not a recognised name.

    """
    return _CLASSES[_canonical(method)](circuit)


def available_methods():
    """Return the canonical method names, for use in a GUI dropdown.

    Returns:
        list[str]: the three supported formulations, in display order.

    """
    return [EXTENDED_TABLEAU, MODIFIED_NODAL, SPARSE_TABLEAU]
