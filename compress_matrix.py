"""Komprimierung eines linearen Systems A*x = rhs auf eine Zielvariable.

Die Zielvariable wird über ihren nullbasierten Spaltenindex angegeben.
Die Komprimierungsstruktur wird mithilfe von `mna.value_dict` numerisch
bestimmt. Mit `return_symbolic=True` werden zusätzlich die unveränderten
symbolischen Ausdrücke derselben komprimierten Zeilen und Spalten ausgegeben.
"""

from operator import index as _index
import importlib


import sympy as sp

try:
    from scipy.sparse import issparse as _issparse
except ImportError:  # SciPy ist nur nötig, wenn eine Sparse-Matrix übergeben wird.
    def _issparse(_value):
        return False


def _to_sympy_matrix(value):
    """Konvertiert SymPy-, NumPy-, SciPy-Sparse- oder Listen-Eingaben."""
    if _issparse(value):
        value = value.toarray()
    if isinstance(value, sp.MatrixBase):
        return sp.Matrix(value)
    if hasattr(value, "tolist"):
        value = value.tolist()
    return sp.Matrix(value)


def _get_value_dict(value_dict):
    """Liest Ersetzungen explizit oder aus ``mna.value_dict``.

    Ein explizites ``value_dict`` ist besonders bei Tests und dann sinnvoll,
    wenn ``mna`` nicht als importierbares Modul vorliegt.
    """
    if value_dict is not None:
        return dict(value_dict)

    # Erst ein eventuell im Modul gesetztes mna-Objekt nutzen, dann das Modul
    # importieren. globals() allein findet mna nicht im aufrufenden Modul.
    mna_object = globals().get("mna")
    if mna_object is None:
        try:
            mna_object = importlib.import_module("mna")
        except ImportError:
            mna_object = None

    return dict(getattr(mna_object, "value_dict", {}) or {})


def _substitute_matrix(matrix, values):
    """Setzt bekannte numerische Werte ein und vereinfacht Matrixeinträge."""
    if not values:
        return matrix.applyfunc(sp.simplify)
    return matrix.applyfunc(
        lambda expr: sp.simplify(expr.subs(values, simultaneous=True))
    )


def _is_nonzero(value):
    """Entscheidet die Graphstruktur anhand des ausgewerteten Eintrags.

    Noch nicht numerisch auswertbare symbolische Ausdrücke werden konservativ
    als Nichtnull behandelt.
    """
    value = sp.simplify(value)
    if value == 0 or value.is_zero is True:
        return False
    if value.is_zero is False:
        return True

    try:
        result = value.equals(0)
    except (TypeError, ValueError, NotImplementedError):
        result = None
    if result is not None:
        return not result

    return True


def _eliminate_single_variable_equations(pattern, target_index):
    """Entfernt iterativ Zeilen zu Nicht-Zielspalten mit Grad eins."""
    n_rows, n_cols = pattern.shape
    active_rows = set(range(n_rows))
    active_cols = set(range(n_cols))

    while True:
        candidate = None
        for col in sorted(active_cols):
            if col == target_index:
                continue
            connected_rows = [
                row for row in sorted(active_rows)
                if _is_nonzero(pattern[row, col])
            ]
            if len(connected_rows) == 1:
                candidate = (connected_rows[0], col)
                break

        if candidate is None:
            break

        row_to_remove, col_to_remove = candidate
        active_rows.remove(row_to_remove)
        active_cols.remove(col_to_remove)

    return active_rows, active_cols


def _target_component(pattern, active_rows, active_cols, target_index):
    """Liefert den zusammenhängenden Bipartit-Graphblock der Zielspalte."""
    visited_rows = set()
    visited_cols = {target_index}
    pending_cols = [target_index]

    while pending_cols:
        col = pending_cols.pop()
        for row in active_rows:
            if row in visited_rows or not _is_nonzero(pattern[row, col]):
                continue
            visited_rows.add(row)
            for other_col in active_cols:
                if (other_col not in visited_cols
                        and _is_nonzero(pattern[row, other_col])):
                    visited_cols.add(other_col)
                    pending_cols.append(other_col)

    return visited_rows, visited_cols


def CompressMatrix(matrix, unknowns, rhs, k, value_dict, return_symbolic=False):
    """Komprimiert ``A*x = rhs`` auf den für Spalte ``k`` relevanten Block.

    Parameter
    ---------
    matrix : Matrix-ähnlich
        Systemmatrix A (SymPy, NumPy, SciPy-Sparse oder verschachtelte Liste).
    rhs : Vektor-ähnlich
        Rechte Seite des Systems. Wird als Spaltenvektor zurückgegeben.
    k : int
        Nullbasierter Spaltenindex der gesuchten Variable.
    value_dict : Mapping, optional
        Numerische Ersetzungen. Standardmäßig wird ``mna.value_dict`` verwendet.
    return_symbolic : bool, optional
        Wenn ``True``, werden zusätzlich die symbolischen Teilmatrizen
        zurückgegeben. Die Rückgabe lautet dann
        ``(A_num, rhs_num, k_new, A_sym, rhs_sym)``.

    Returns
    -------
    Ohne ``return_symbolic``:
        ``(A_num, rhs_num, k_new)``
    Mit ``return_symbolic=True``:
        ``(A_num, rhs_num, k_new, A_sym, rhs_sym)``

    
    """
    A_sym = _to_sympy_matrix(matrix)
    b_sym = _to_sympy_matrix(rhs)

    if b_sym.rows == 1 and b_sym.cols == A_sym.rows:
        b_sym = b_sym.T
    elif b_sym.cols != 1:
        raise ValueError("rhs muss ein Vektor oder ein Spaltenvektor sein.")

    if b_sym.rows != A_sym.rows:
        raise ValueError(
            f"Dimensionen passen nicht zusammen: A hat {A_sym.rows} Zeilen, "
            f"rhs hat {b_sym.rows} Einträge."
        )

    try:
        k = _index(k)
    except TypeError as exc:
        raise TypeError("k muss ein ganzzahliger, nullbasierter Index sein.") from exc

    if not 0 <= k < A_sym.cols:
        raise IndexError(f"Zielindex k={k} liegt außerhalb von 0..{A_sym.cols - 1}.")

    values = value_dict
    A_num_eval = _substitute_matrix(A_sym, values)
    b_num_eval = _substitute_matrix(b_sym, values)

    # Die numerische Struktur entscheidet, welche Zeilen und Spalten relevant
    # sind. Symbolische Einträge werden anschließend mit denselben Indizes
    # extrahiert, damit keine Symbolinformation verloren geht.
    active_rows, active_cols = _eliminate_single_variable_equations(A_num_eval, k)
    rows_in_component, cols_in_component = _target_component(
        A_num_eval, active_rows, active_cols, k
    )

    rows_keep = sorted(rows_in_component)
    cols_keep = sorted(cols_in_component)

    A_num = A_num_eval.extract(rows_keep, cols_keep)
    rhs_num = sp.Matrix(len(rows_keep), 1, [b_num_eval[row, 0] for row in rows_keep])
    A_compressed_symbolic = A_sym.extract(rows_keep, cols_keep)
    rhs_compressed_symbolic = sp.Matrix(
        len(rows_keep), 1, [b_sym[row, 0] for row in rows_keep]
    )
    k_new = cols_keep.index(k)

    if return_symbolic:
        unknowns_compressed = unknowns.extract(cols_keep, [0])
        return (
            A_num,
            rhs_num,
            k_new,
            A_compressed_symbolic,
            rhs_compressed_symbolic,
            unknowns_compressed
        )
    return A_num, rhs_num, k_new
