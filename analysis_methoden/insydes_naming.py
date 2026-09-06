"""Analog Insydes style names for an equation system.

Insydes prints the tableau unknowns as V<sep><branch> and I<sep><branch>,
joins a flattened model element to its instance (RPI_Q1), calls the bipolar
model's controlled source VCS and prefixes its controlling port with CS
(CS_VCS_Q1). Element values are named after the model parameter rather than
after the element, so the transconductance of Q1 reads gm_Q1 while its
branch reads VCS_Q1.

Insydes itself writes "$" where this module writes "_" (gm$Q1, V$RPI$Q1).
The underscore is used instead because it is the separator the rest of this
project flattens with, and because "$" is not a legal Python identifier:
sympify() rejects it. Set SEPARATOR and the three prefixes below back to "$"
to get Insydes' own spelling.

Only the presentation is translated, the sympy symbols inside the matrix keep
the names the analysis built them with (G_Q1, RPI_Q1, ...). solve() takes the
name of an unknown as a string, so renaming the symbols themselves would
change that API for every caller.

Usage:
    import analysis_methoden.insydes_naming as ins

    mapping = ins.symbol_map(analysis)
    print(ins.render(analysis.T[i, j], mapping))
    print(ins.unknown_labels(analysis))
"""

import sympy as sp

SEPARATOR = "_"
VOLTAGE_PREFIX = "V_"
CURRENT_PREFIX = "I_"
CONTROL_PREFIX = "CS_"

# Insydes renames the controlled source of a transistor model after its kind.
# Only the VCCS spelling is confirmed against real Insydes output (V$VCS$Q1 /
# V$CS$VCS$Q1); add the other three once they have been seen, an element whose
# type is not listed here keeps its netlist name.
CONTROLLED_SOURCE_NAMES = {
    "G": "VCS",
}

# params key written by Element.remap_values, holding the model parameter name
PARAM_NAME_KEY = "param_name"


def _parts(element, separator):
    """Split a flattened element name into [model element, instance, ...]."""
    if not separator:
        return [element.name]
    return [part for part in element.name.split(separator) if part]


def branch_base_name(element, separator):
    """Insydes name of the branch an element occupies, e.g. RPI$Q1, VCS$Q1."""
    parts = _parts(element, separator)
    head, tail = parts[0], parts[1:]

    element_type = element.type.upper()
    if element_type in CONTROLLED_SOURCE_NAMES and head.upper() == element_type:
        # only the bare model source (named "G" in BJT_BasicModel.json) is
        # renamed, a user's own G1 in the netlist keeps its name
        head = CONTROLLED_SOURCE_NAMES[element_type]

    return SEPARATOR.join([head.upper()] + [part.upper() for part in tail])


def branch_name(branch, separator):
    """Insydes name of a Branch, controlling ports included."""
    base = branch_base_name(branch.element, separator)
    return f"{CONTROL_PREFIX}{base}" if branch.is_control else base


def value_name(element, separator):
    """Insydes name of an element's value, e.g. gm$Q1, rpi$Q1, CB.

    Elements that came out of a transistor model are named after the model
    parameter; everything else keeps its netlist name.
    """
    parts = _parts(element, separator)
    param = element.params.get(PARAM_NAME_KEY, "")

    if not param:
        # no .out file was loaded, so remap_values never ran and the parameter
        # name is still sitting in the value slot
        raw = element.params.get(
            "value" if element.type.upper() in ("E", "F", "G", "H") else "value_dc", "")
        if raw and not raw[0].isdigit() and not raw.startswith((".", "-", "+")):
            param = raw

    if param and len(parts) > 1:
        return SEPARATOR.join([param] + [part.upper() for part in parts[1:]])

    return SEPARATOR.join(part.upper() for part in parts)


def _separator_of(analysis):
    """The separator the circuit was flattened with, "." if unknown."""
    return getattr(getattr(analysis, "ct", None), "separator", ".")


def symbol_map(analysis):
    """Map every element symbol in the matrix onto its Insydes name.

    Returns:
        dict: {sympy.Symbol: sympy.Symbol}, ready for expr.subs().

    """
    separator = _separator_of(analysis)
    circuit = getattr(analysis, "ct", None)
    if circuit is None:
        return {}

    mapping = {}
    for element in circuit.elements:
        source = sp.Symbol(element.get_symbol())
        target = sp.Symbol(value_name(element, separator))
        if source != target:
            mapping[source] = target

    return mapping


def render(expression, mapping):
    """Print one matrix cell with Insydes names substituted in."""
    if not mapping or not getattr(expression, "free_symbols", None):
        return str(expression)
    return str(expression.subs(mapping))


def unknown_labels(analysis):
    """Insydes labels of the unknown vector, in the analysis' own order.

    Falls back to the analysis' plain labels for formulations that have no
    branches, i.e. modified nodal analysis.
    """
    branches = getattr(analysis, "branches", None)
    if not branches:
        return analysis.get_unknowns_as_strings()

    separator = _separator_of(analysis)
    names = [branch_name(branch, separator) for branch in branches]

    labels = ([f"{VOLTAGE_PREFIX}{name}" for name in names]
              + [f"{CURRENT_PREFIX}{name}" for name in names])

    # the extended tableau carries the node potentials after [u | i]
    node_map = getattr(analysis, "node_map", {})
    if len(analysis.get_unknowns_as_strings()) > len(labels):
        nodes = [""] * (len(analysis.get_unknowns_as_strings()) - len(labels))
        for name, index in node_map.items():
            if index != 0 and index - 1 < len(nodes):
                nodes[index - 1] = f"{VOLTAGE_PREFIX}{name.upper()}"
        labels += nodes

    return labels


def row_labels(analysis):
    """Insydes labels for the rows, [KVL | KCL | element eqs.] for the normal
    tableau and [U def. | KCL | element eqs.] for the extended one.
    """
    branches = getattr(analysis, "branches", None)
    if not branches:
        return [str(i + 1) for i in range(analysis.get_equation_system()[0].rows)]

    separator = _separator_of(analysis)
    names = [branch_name(branch, separator) for branch in branches]

    inverse_node_map = {index: name
                        for name, index in getattr(analysis, "node_map", {}).items()
                        if index != 0}
    kcl = [f"KCL {inverse_node_map.get(index, index)}"
           for index in range(1, getattr(analysis, "n", 0) + 1)]
    element_equations = [f"EL {name}" for name in names]

    if hasattr(analysis, "l"):
        links = getattr(analysis, "links", [])
        kvl = [f"KVL {names[j]}" for j in links]
        return kvl + kcl + element_equations

    return [f"U {name}" for name in names] + kcl + element_equations
