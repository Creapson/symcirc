import numpy as np
import pandas as pd
import sympy as sp
import scipy.linalg as la
from scipy.linalg import qz, solve_triangular, eig
from time import perf_counter_ns
import warnings



def get_eigenvalues(A_s, s):
    """
    Berechnet die verallgemeinerten Eigenwerte von

        A(s) = A0 - s * B

    und gibt sie zusammen mit ihrem Index zurück.
    """

    if not isinstance(A_s, sp.MatrixBase):
        A_s = sp.Matrix(A_s)

    # A(s) = A0 - s*B
    A0 = A_s.subs(s, 0)
    B = -A_s.applyfunc(lambda x: sp.expand(x).coeff(s, 1))

    # Numerische Matrizen
    A0 = np.asarray(A0, dtype=np.complex128)
    B = np.asarray(B, dtype=np.complex128)

    # QZ-Zerlegung
    t_0 = perf_counter_ns()
    S, T, Q, Z = qz(A0, B, output="complex")
    t_1 = perf_counter_ns()

    print(f"QZ-Zerlegung in {(t_1 - t_0) / 1e6:.3f} ms")

    alpha = np.diag(S)
    beta = np.diag(T)

    with np.errstate(divide="ignore", invalid="ignore"):
        eigenvalues = alpha / beta

    # Ausgabe
    
    print("Verallgemeinerte Eigenwerte:")
    print("-" * 40)

    for i, eigval in enumerate(eigenvalues):
        if np.isfinite(eigval):
            print(f"[{i}]  {eigval}")
        else:
            print(f"[{i}]  ∞")

    return eigenvalues, S, T, Q, Z




def eigenvalue_term_ranking(
    A_s,
    s,
    mna,
    pole_index,
    epsilon_max,
    residual_max, 
    mac_min, 
    iteration_max, 
    error_metric="absolute",
    ranking_metric="norm",
    number_of_test_points_singularity=3,
    simplify_roots=False,
    w = None,
    w_tilde = None,
    y_tilde = None,
    check_exact=False,
):
    """
    Eigenwertbasiertes Ranking einzelner symbolischer Terme von A(s).

    Es wird die Darstellung

        A(s) = A0 - s * B

    verwendet.

    Jeder additive Term eines symbolischen Matrixeintrags wird separat
    betrachtet. Für einen Term t(s) gilt:

        t(s) = t_A - s * t_B

    mit

        t_A = t(s=0)
        t_B = -dt/ds

    Wird dieser Term vollständig entfernt, ergibt sich:

        Delta A = -t_A * E_ij
        Delta B = -t_B * E_ij

    und damit die lineare Eigenwertverschiebung

        Delta lambda ≈
            vᴴ (Delta A - lambda0 Delta B) u
            --------------------------------
                      vᴴ B u

    Parameter
    ----------
    A_s : sympy.Matrix
        Symbolische Systemmatrix A(s).

    s : sympy.Symbol
        Symbol der Eigenwert-/Polvariable.

    mna
        Objekt mit mna.value_dict zur numerischen Substitution der
        symbolischen Parameter.

    pole_index : int
        Index des vorher ausgewählten Eigenwerts.

    metric : {"absolute", "relative", "real", "imag"}
        Ranking-Kriterium:

        "absolute":
            |Delta lambda|

        "relative":
            |Delta lambda / lambda0|

        "real":
            |Re(Delta lambda)|

        "imag":
            |Im(Delta lambda)|

    check_exact : bool
        Falls True, wird für jeden Term zusätzlich das Eigenwertproblem
        nach vollständiger Entfernung des Terms erneut gelöst.

    Returns
    -------
    ranking : pandas.DataFrame
        Sortiertes Ranking der einzelnen symbolischen Terme.

    info : dict
        Informationen zum ausgewählten Eigenwert und zu den
        Eigenvektoren.
    """

    # ==========================================================
    # 1. Eingabematrix vorbereiten
    # ==========================================================
    if not isinstance(A_s, sp.MatrixBase):
        A_s = sp.Matrix(A_s)

    A_s = A_s.applyfunc(sp.expand)

    if s not in A_s.free_symbols:
        raise ValueError(
            "Das angegebene Symbol s kommt nicht in A_s vor."
        )

    # ==========================================================
    # 2. Prüfen, ob A(s) linear in s ist
    # ==========================================================
    for expr in A_s:
        if sp.expand(expr).coeff(s, 2) != 0:
            raise ValueError(
                "A_s muss linear in s sein: A(s) = A0 - s*B."
            )

        # zusätzliche Prüfung auf höhere Potenzen
        if sp.degree(expr, s) is not None and sp.degree(expr, s) > 1:
            raise ValueError(
                "A_s muss linear in s sein: A(s) = A0 - s*B."
            )

    # ==========================================================
    # 3. Symbolische Zerlegung A(s) = A0 - s B
    # ==========================================================
    A0_sym = A_s.subs(s, 0)
    B_sym = -A_s.diff(s)

    # ==========================================================
    # 4. Numerische Matrizen erzeugen
    # ==========================================================
    try:
        A0_num_sym = A0_sym.subs(mna.value_dict)
        B_num_sym = B_sym.subs(mna.value_dict)

        A0 = np.asarray(
            A0_num_sym,
            dtype=np.complex128
        )

        B = np.asarray(
            B_num_sym,
            dtype=np.complex128
        )

    except Exception as exc:
        raise ValueError(
            "A0 oder B konnten mit mna.value_dict nicht "
            "numerisch ausgewertet werden."
        ) from exc

    # ==========================================================
    # 5. QZ-Zerlegung
    #
    # A0 u = lambda B u
    # ==========================================================
    S, T, Q, Z = qz(
        A0,
        B,
        output="complex"
    )

    alpha = np.diag(S)
    beta = np.diag(T)

    with np.errstate(divide="ignore", invalid="ignore"):
        eigenvalues_qz = alpha / beta

    # ==========================================================
    # 6. Ausgewählten Eigenwert bestimmen
    # ==========================================================
    if pole_index < 0 or pole_index >= len(eigenvalues_qz):
        raise IndexError(
            f"pole_index={pole_index} ist ungültig. "
            f"Erlaubt sind 0 bis {len(eigenvalues_qz) - 1}."
        )

    lambda0 = eigenvalues_qz[pole_index]

    if not np.isfinite(lambda0):
        raise ValueError(
            f"Eigenwert mit Index {pole_index} ist unendlich."
        )

    # ==========================================================
    # 7. Linken und rechten Eigenvektor bestimmen
    # ==========================================================
    eigenvalues, left_vecs, right_vecs = eig(
        A0,
        B,
        left=True,
        right=True
    )

    finite_indices = np.flatnonzero(
        np.isfinite(eigenvalues)
    )

    if len(finite_indices) == 0:
        raise ValueError(
            "Keine endlichen Eigenwerte gefunden."
        )

    # eig() kann die Eigenwerte anders anordnen als qz().
    # Deshalb den Eigenvektor zum gewünschten Eigenwert suchen.
    idx = finite_indices[
        np.argmin(
            np.abs(
                eigenvalues[finite_indices] - lambda0
            )
        )
    ]

    lambda0_eig = eigenvalues[idx]

    # Rechter Eigenvektor u
    u = right_vecs[:, idx].astype(np.complex128)

    # Linker Eigenvektor v
    v = left_vecs[:, idx].astype(np.complex128)

    # Normierung
    u /= np.linalg.norm(u)
    v /= np.linalg.norm(v)

    # ==========================================================
    # 8. Nenner vᴴ B u
    # ==========================================================
    denominator = np.vdot(v, B @ u)

    # if abs(denominator) < 1e-14:
    #     raise np.linalg.LinAlgError(
    #         "vᴴ B u ist numerisch sehr klein. "
    #         "Der Eigenwert ist möglicherweise schlecht konditioniert."
    #     )

    # ==========================================================
    # 9. Alle symbolischen Terme untersuchen
    # ==========================================================
    ranking = []

    for i in range(A_s.rows):
        for j in range(A_s.cols):

            expr = sp.expand(A_s[i, j])

            if expr == 0:
                continue

            # --------------------------------------------------
            # Additive Terme des Matrixeintrags
            #
            # Beispiel:
            # R1 + R2 + s*C1 - s*C2
            #
            # -> R1
            # -> R2
            # -> s*C1
            # -> -s*C2
            # --------------------------------------------------
            terms = sp.Add.make_args(expr)

            for term in terms:

                term = sp.expand(term)

                # ------------------------------------------------
                # Zerlegung des einzelnen Terms:
                #
                # term(s) = term_A - s * term_B
                #
                # term_A = term(s=0)
                # term_B = -d(term)/ds
                # ------------------------------------------------
                term_A = sp.expand(
                    term.subs(s, 0)
                )

                term_B = sp.expand(
                    -sp.diff(term, s)
                )

                # ------------------------------------------------
                # Quelle des Terms bestimmen
                # ------------------------------------------------
                has_A = term_A != 0
                has_B = term_B != 0

                if has_A and has_B:
                    source = "A+B"
                elif has_A:
                    source = "A"
                elif has_B:
                    source = "B"
                else:
                    # Sollte wegen term != 0 eigentlich nicht
                    # vorkommen.
                    continue

                # ------------------------------------------------
                # Numerische Substitution der Parameter
                # ------------------------------------------------
                term_num = sp.expand(
                    term.subs(mna.value_dict)
                )

                term_A_num = sp.expand(
                    term_A.subs(mna.value_dict)
                )

                term_B_num = sp.expand(
                    term_B.subs(mna.value_dict)
                )

                # Prüfen, ob noch unbekannte Symbole vorhanden sind
                remaining_symbols = (
                    term_num.free_symbols - {s}
                )

                if remaining_symbols:
                    raise ValueError(
                        f"Term {term} enthält nach "
                        f"mna.value_dict noch unbekannte Symbole: "
                        f"{remaining_symbols}"
                    )

                # ------------------------------------------------
                # Term am ausgewählten Eigenwert auswerten
                # ------------------------------------------------
                term_at_lambda = complex(
                    sp.N(
                        term_num.subs(
                            s,
                            complex(lambda0)
                        )
                    )
                )

                # ------------------------------------------------
                # Numerische A-/B-Anteile
                # ------------------------------------------------
                term_A_num_value = complex(
                    term_A_num
                )

                term_B_num_value = complex(
                    term_B_num
                )

                # ------------------------------------------------
                # E_ij-Faktor
                #
                # vᴴ E_ij u = conj(v_i) * u_j
                # ------------------------------------------------
                factor = (
                    np.conj(v[i]) * u[j]
                )

                # ------------------------------------------------
                # Lineare Eigenwertverschiebung
                #
                # Delta A = -term_A E_ij
                # Delta B = -term_B E_ij
                #
                # Delta A - lambda Delta B
                # = (-term_A + lambda term_B) E_ij
                # ------------------------------------------------
                delta_lambda = (
                    factor
                    * (
                        -term_A_num_value
                        + lambda0
                        * term_B_num_value
                    )
                    / denominator
                )

               
                # ------------------------------------------------
                # Ranking-Metrik
                # ------------------------------------------------
                if error_metric == "absolute":

                    if ranking_metric == "norm":
                        norm_error = abs(delta_lambda)
                        compare_epsilon = abs(epsilon_max)
                        score = norm_error
                    elif ranking_metric == "real":
                        real_error = abs(delta_lambda.real)
                        compare_epsilon = abs(epsilon_max)
                        score = real_error
                    elif ranking_metric == "imag":
                        imag_error = abs(delta_lambda.imag)
                        compare_epsilon = abs(epsilon_max)
                        score = imag_error

                    else:
                        raise ValueError(
                            "ranking_metric muss 'norm', 'real' oder 'imag' sein."
                        )

                elif error_metric == "relative":

                    

                    if abs(lambda0) < 1e-15:
                        relative_error = np.inf
                        score = relative_error

                                        
                    elif ranking_metric == "norm":
                        norm_relative_error = abs(delta_lambda) / abs(lambda0)
                        compare_epsilon = epsilon_max*abs(lambda0)
                        score = norm_relative_error

                    elif ranking_metric == "real":
                        real_relative_error = abs(delta_lambda.real) / abs(lambda0.real)
                        compare_epsilon = epsilon_max*abs(lambda0.real)
                        score = real_relative_error

                    elif ranking_metric == "imag":
                        imag_relative_error = abs(delta_lambda.imag) / abs(lambda0.imag)
                        compare_epsilon = epsilon_max*abs(lambda0.imag)
                        score = imag_relative_error

                    else:
                        raise ValueError(
                            "ranking_metric muss 'norm', 'real' oder 'imag' sein."
                        )

                else:
                    raise ValueError(
                        "error_metric muss 'absolute' oder 'relative' sein."
                    )

                ranking.append(
                                        {
                                            "row": i,
                                            "col": j,
                
                                            # Ursprünglicher symbolischer Term
                                            "term": term,
                
                                            # Explizite Zuordnung zu A/B
                                            "source": source,
                                            "A_term": term_A,
                                            "B_term": term_B,
                
                                            # Numerische Darstellung
                                            "numeric_term": term_num,
                                            "numeric_A_term": term_A_num_value,
                                            "numeric_B_term": term_B_num_value,
                                            "term_at_lambda": term_at_lambda,
                
                                            # Ranking
                                            "score": score,
                                        }
                                    )
                    

    # ==========================================================
    # 10. Ranking sortieren
    # ==========================================================
    info = pd.DataFrame(ranking)

    if info.empty:
        raise ValueError(
            "Es wurden keine nichtverschwindenden Terme gefunden."
        )

    info = (
        info
        .sort_values(
            by="score",
            ascending=True
        )
        .reset_index(drop=True)
    )

    info.insert(
        0,
        "rank",
        np.arange(1, len(ranking) + 1)
    )

    # ==========================================================
    # 11. Optionale exakte Berechnung
    # ==========================================================
    if check_exact:

        exact_lambda = []
        exact_delta = []
        linearization_ratio = []

        for entry in ranking.itertuples():

            i = int(entry.row)
            j = int(entry.col)

            # Symbolische Terme
            term_A = entry.A_term
            term_B = entry.B_term

            # Numerische Werte
            term_A_num = complex(
                sp.N(
                    term_A.subs(
                        mna.value_dict
                    )
                )
            )

            term_B_num = complex(
                sp.N(
                    term_B.subs(
                        mna.value_dict
                    )
                )
            )

            # Kopien der Matrizen
            A0_removed = A0.copy()
            B_removed = B.copy()

            # Entfernen des Terms:
            #
            # A0' = A0 - term_A E_ij
            # B'  = B  - term_B E_ij
            #
            A0_removed[i, j] -= term_A_num
            B_removed[i, j] -= term_B_num

            # Neues Eigenwertproblem
            eigenvalues_removed = eig(
                A0_removed,
                B_removed,
                left=False,
                right=False
            )

            finite_removed = (
                eigenvalues_removed[
                    np.isfinite(eigenvalues_removed)
                ]
            )

            if len(finite_removed) == 0:

                lambda_exact = np.nan + 1j * np.nan
                delta_exact = np.nan + 1j * np.nan
                ratio = np.nan

            else:

                # Eigenwert verfolgen, der dem ursprünglichen
                # Eigenwert am nächsten liegt.
                nearest_idx = np.argmin(
                    np.abs(
                        finite_removed - lambda0
                    )
                )

                lambda_exact = (
                    finite_removed[nearest_idx]
                )

                delta_exact = (
                    lambda_exact - lambda0
                )

                if abs(entry.delta_lambda) > 1e-15:
                    ratio = (
                        abs(delta_exact)
                        / abs(entry.delta_lambda)
                    )
                else:
                    ratio = np.nan

            exact_lambda.append(
                lambda_exact
            )
            exact_delta.append(
                delta_exact
            )
            linearization_ratio.append(
                ratio
            )

        ranking["exact_lambda_removed"] = exact_lambda
        ranking["exact_delta_lambda"] = exact_delta
        ranking["linearization_ratio"] = (
            linearization_ratio
        )

    # ==========================================================
    # 12. Loop setup
    # ==========================================================
    A0_trial = A0.copy()
    B_trial = B.copy()

    A0_sym_trial = A0_sym.copy()
    B_sym_trial = B_sym.copy()

    lambda_test = lambda0
    u_test = u.copy()

    for parameter in ranking:
        if parameter["source"] == "A":
            A0_trial[parameter["row"], parameter["col"]] -= parameter["numeric_A_term"]
            A0_sym_trial[parameter["row"], parameter["col"]] -= parameter["A_term"]
        elif parameter["source"] == "B":
            B_trial[parameter["row"], parameter["col"]] += parameter["numeric_B_term"]
            B_sym_trial[parameter["row"], parameter["col"]] += parameter["B_term"]

        singularity_test_points = choose_lu_test_points(
            A0_trial,
            B_trial,
            count=number_of_test_points_singularity)

        if any(
            quasi_singularity_check(
                A0_trial,
                B_trial,
                s=s_test,
                rcond_tol=1e-12
            )
            for s_test in singularity_test_points
        ):
            A0_trial[parameter["row"], parameter["col"]] += parameter["numeric_A_term"]      
            A0_sym_trial[parameter["row"], parameter["col"]] += parameter["A_term"]
            B_trial[parameter["row"], parameter["col"]] -= parameter["numeric_B_term"]
            B_sym_trial[parameter["row"], parameter["col"]] -= parameter["B_term"]

            continue

        lambda_corrected, y, residual_norm, iteration = JacobiCorrection(
            A0_trial,
            B_trial,
            lambda_test,
            u_test,
            u,
            v,
            residual_max,
            mac_min,
            iteration_max
            )

        update_eigenpair = (iteration == iteration_max) and (residual_norm > residual_max)

        update_eigenpair = update_eigenpair or (modal_assurance_criterion(y, u) < mac_min)

        if error_metric == "absolute":

                    if ranking_metric == "norm":
                        norm_error = abs(lambda_corrected - lambda0)
                        update_error = norm_error
                    elif ranking_metric == "real":
                        real_error = abs(lambda_corrected.real - lambda0.real)
                        update_error = real_error
                    elif ranking_metric == "imag":
                        imag_error = abs(lambda_corrected.imag - lambda0.imag)
                        update_error = imag_error


        elif error_metric == "relative":

                                        
                    if ranking_metric == "norm":
                        norm_relative_error = abs(lambda_corrected - lambda0) / abs(lambda0)
                        update_error = norm_relative_error

                    elif ranking_metric == "real":
                        real_relative_error = abs(lambda_corrected.real - lambda0.real) / abs(lambda0.real)
                        update_error = real_relative_error

                    elif ranking_metric == "imag":
                        imag_relative_error = abs(lambda_corrected.imag - lambda0.imag) / abs(lambda0.imag)
                        update_error = imag_relative_error        

        update_eigenpair = update_eigenpair or (update_error > epsilon_max)

        if not update_eigenpair:
            lambda_test = lambda_corrected
            u_test = y

        else:
            A0_trial[parameter["row"], parameter["col"]] += parameter["numeric_A_term"]      
            A0_sym_trial[parameter["row"], parameter["col"]] += parameter["A_term"]
            B_trial[parameter["row"], parameter["col"]] -= parameter["numeric_B_term"]
            B_sym_trial[parameter["row"], parameter["col"]] -= parameter["B_term"]


    determinant = sp.det(A0_sym_trial - s * B_sym_trial)

    
    roots = sp.solve(determinant, s)

    if simplify_roots == True:
        roots = [sp.simplify(root) for root in roots]

    return info, ranking, determinant, roots
    

    

#u - right eigenvector

def right_eigenvector_from_qz(S, T, lam, k, Z):
    M = S - lam * T
    n = S.shape[0]

    y = np.zeros(n, dtype=np.result_type(S, T, lam))
    y[k] = 1.0

    if k > 0:
        y[:k] = solve_triangular(
            M[:k, :k],
            -M[:k, k],
            lower=False,
        )

    return Z @ y

#v - left eigenvector

def left_eigenvector_from_qz(S, T, lam, k, Q):
    M = S - lam * T
    n = S.shape[0]

    w = np.zeros(n, dtype=np.result_type(S, T, lam))
    w[k] = 1.0

    if k < n - 1:
        w[k + 1:] = solve_triangular(
            M[k + 1:, k + 1:].conj().T,
            -M[k + 1:, k].conj(),
            lower=True,
        )

    return Q @ w

def modal_assurance_criterion(v, u):
    """
    Berechnet das Modal Assurance Criterion (MAC) zwischen zwei Vektoren.

    Parameters
    ----------
    u : np.ndarray
        Erster Vektor 
    v : np.ndarray
        Zweiter Vektor 

    Returns
    -------
    mac : float
        Das Modal Assurance Criterion (MAC) zwischen den beiden Vektoren.
    """
    numerator = np.abs(np.vdot(v, u)) ** 2
    denominator = np.vdot(v, v) * np.vdot(u, u) 

    if denominator == 0:
        raise ValueError("Einer der Vektoren ist der Nullvektor.")

    mac = numerator / denominator
    return mac

def JacobiCorrection(A_test_num, 
                     B_test_num, 
                     lambda_test, 
                     u_test, 
                     u_nominal, 
                     v_nominal, 
                     residual_max, 
                     mac_min, 
                     iteration_max, 
                     w = None,
                     w_tilde = None,
                     y_tilde = None
                       ):
    """
    Berechnet die Jacobi-Korrektur für einen Eigenwert und Eigenvektor.

    Parameters
    ----------
    A_test_num : np.ndarray
        Die Matrix A des Eigenwertproblems.
    B_test_num : np.ndarray
        Die Matrix B des Eigenwertproblems.
    lambda_test : complex
        Der aktuelle Eigenwert.
    u_test : np.ndarray
        Der aktuelle rechte Eigenvektor.
    u_nominal : np.ndarray
        Der nominale rechte Eigenvektor.
    v_nominal : np.ndarray
        Der nominale linke Eigenvektor.
    residual_max : float
        Maximale Residualnorm für die Konvergenzprüfung.
    mac_min : float
        Minimale MAC (Modal Assurance Criterion) für die Konvergenzprüfung.
    iteration_max : int
        Maximale Anzahl an Iterationen.

    Returns
    -------
    lambda_corrected : complex
        Der korrigierte Eigenwert.
    u_corrected : np.ndarray
        Der korrigierte rechte Eigenvektor.
    residual_norm : float
        Die Norm des Residuals nach der letzten Iteration.
    """
    
    if w is None:
        w = v_nominal

    if w_tilde is None:
        w_tilde = w

    if y_tilde is None:
        y_tilde = u_nominal

    A_test_num = np.asarray(A_test_num, dtype=np.complex128)
    B_test_num = np.asarray(B_test_num, dtype=np.complex128)
    y = np.asarray(u_test, dtype=np.complex128).copy()
    u_nominal = np.asarray(u_nominal, dtype=np.complex128)
    v_nominal = np.asarray(v_nominal, dtype=np.complex128)

    iteration = 0

    while iteration <= iteration_max:

        y_norm = la.norm(y)

        if y_norm == 0.0:
            raise np.linalg.LinAlgError("Breakdown: approximate eigenvector has zero norm")
        y = y / y_norm

        Ay = A_test_num @ y
        By = B_test_num @ y

        lambda_test = np.vdot(w_tilde, Ay) / np.vdot(w_tilde, By)

        residual = Ay - lambda_test * By
        residual_norm = float(la.norm(residual))

        mac = modal_assurance_criterion(y, u_nominal)

        if residual_norm < residual_max or mac < mac_min or iteration == iteration_max:
            return lambda_test, y, residual_norm, iteration

        M = A_test_num - lambda_test * B_test_num

        n = M.shape[0]
        K = np.empty((n + 1, n + 1), dtype=np.complex128)
        K[:n, :n] = M
        K[:n, n] = w_tilde
        K[n, :n] = np.conjugate(y_tilde)
        K[n, n] = 0.0
        b = np.empty(n + 1, dtype=K.dtype)
        b[:n] = -residual
        b[n] = 0.0
        # check_finite=False matters for tight iteration loops.
        sol = la.solve(K, b, assume_a="gen", check_finite=False, overwrite_a=True,
                    overwrite_b=True)
        z = sol[:n]

        y = y + z

        iteration += 1


def quasi_singularity_check(
    A0,
    B0,
    s,
    *,
    rcond_tol = None,
):
    """Check ``A0 + s*B0`` for numerical quasi-singularity using LU.

    This implements the statement from the supplied text literally at the
    matrix level: form ``M = A0 + s*B0`` and factor it with LU.  Exact
    singularity is detected from the LU factorization.  Since the source
    does not prescribe a numerical threshold for *quasi*-singularity, the
    optional ``rcond_tol`` controls that additional numerical classification.

    ``rcond`` is an estimate of 1/cond_1(M), obtained from the same LU
    factorization.  A small value therefore means that M is nearly singular.

    ``value_dict`` can be used for SymPy matrices; substitution is performed
    once before the LU factorization.
    """
    M = np.asarray(A0 + s * B0, dtype=np.complex128)
    n = M.shape[0]
    if M.shape != (n, n):
        raise ValueError("A0 + s*B0 must be square")

    # LAPACK GETRF returns a singularity indication through a zero pivot;
    # scipy.linalg.lu_factor may also emit a LinAlgWarning, but the resulting
    # LU factors are still usable for the rcond estimate.
    #with np.errstate(all="ignore"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=la.LinAlgWarning)
        lu, piv = la.lu_factor(M, check_finite=False, overwrite_a=False)

    diag_u = np.abs(np.diag(lu))
    singular = bool(np.any(diag_u == 0.0))

    # Re-use the LU factorization for an inexpensive reciprocal condition
    # estimate rather than calling an SVD or a full inverse-norm computation.
    anorm = float(la.norm(M, 1))
    gecon = la.lapack.get_lapack_funcs("gecon", (lu,))
    rcond, info = gecon(lu, anorm, norm="1")
    rcond = float(rcond)

    if rcond_tol is None:
        quasi = singular
    else:
        if rcond_tol <= 0.0:
            raise ValueError("rcond_tol must be > 0")
        quasi = singular or (rcond < rcond_tol)

    return quasi


def choose_lu_test_points(
    A0,
    B0,
    *,
    count = 3,
):
    """Return generic complex test points on the scale ||A||_1 / ||B||_1.

    No universal ``s`` is prescribed by the source.  For a dimensionally and
    numerically balanced choice, the magnitude is chosen so that ``A`` and
    ``s*B`` have comparable 1-norms, while the points are placed off the real
    axis.  The values are intentionally not tied to the eigenvalues.
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    a = float(la.norm(np.asarray(A0), 1))
    b = float(la.norm(np.asarray(B0), 1))
    if b == 0.0:
        scale = 1.0
    else:
        scale = a / b if a > 0.0 else 1.0

    angles = np.linspace(np.pi / 4.0, 3.0 * np.pi / 4.0, count)
    return scale * np.exp(1j * angles)