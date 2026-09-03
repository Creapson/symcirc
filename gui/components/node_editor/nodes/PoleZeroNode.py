"""
[TR] Pol/sifir dugumu: bir transfer fonksiyonu H(s)'in kutuplarini ve
sifirlarini bulur ve s-duzleminde cizer.

Iki yol:
  * Sayisal: MNA sistemi s'de tam olarak afindir, A(s) = G + s*C_dyn.
    Kutuplar det(G + s*C_dyn) = 0, yani genellestirilmis ozdeger problemi
    eig(G, -C_dyn). Sifirlar Cramer payi det(A_out(s)) uzerinden (cikis
    sutunu kaynak vektoru z ile degistirilir) yine bir ozdeger problemiyle.
  * Sembolik: H(s) = det(A_out(s)) / det(A(s)) tam rasyonel olarak. Kuplaj
    kondansatorlerinden gelen s = 0 kutup/sifirlari TAM cikar.

[EN] Pole/zero node: finds the poles and zeros of a transfer function H(s)
and plots them on the s-plane.

Two paths:
  * Numeric: the MNA system is exactly affine in s, A(s) = G + s*C_dyn.
    Poles solve det(G + s*C_dyn) = 0, i.e. the generalized eigenproblem
    eig(G, -C_dyn). Zeros come from the Cramer numerator det(A_out(s))
    (output column replaced by the source vector z) via a second
    eigenproblem.
  * Symbolic: H(s) = det(A_out(s)) / det(A(s)) as an exact rational. The
    s = 0 poles/zeros from coupling capacitors come out EXACT.
"""

import dearpygui.dearpygui as dpg
import numpy as np
import sympy as sp
from pydantic import Field
from typing import Literal, List
import scipy.linalg as scipy
from gui.components.node_editor.nodes.Node import Node, NodeType

class PoleZeroNode(Node):
    node_type: Literal[NodeType.POLE_ZERO_PLOT] = NodeType.POLE_ZERO_PLOT

    zeros: List[complex] = Field(default_factory=list, exclude=True)
    poles: List[complex] = Field(default_factory=list, exclude=True)

    text_zeros_tag: str = Field(default="", exclude=True)
    text_poles_tag: str = Field(default="", exclude=True)
    scatter_zeros_tag: str = Field(default="", exclude=True)
    scatter_poles_tag: str = Field(default="", exclude=True)
    symbolic_tf_tag: str = Field(default="", exclude=True)
    source_info_tag: str = Field(default="", exclude=True)

    src_mode: str = Field(default="", exclude=True)          # "numeric" | "symbolic"
    src_output_node: str = Field(default="", exclude=True)

    def build(self):
        self.add_input_pin("mna_pin", "Connect a TransferFunction node here!")

        with self.add_static_attr():
            dpg.add_button(label="Calculate & Plot", callback=self.calculate_callback)

            self.source_info_tag = self.uuid("source_info")
            dpg.add_text("Kaynak: bir TransferFunction dugumu baglayin.",
                         tag=self.source_info_tag, color=[150, 150, 150], wrap=340)
            dpg.add_text("Cikis dugumu ve sembolik/sayisal secimi bagli olan "
                         "TransferFunction dugumunden alinir.", color=[150, 150, 150],
                         wrap=340)
            dpg.add_separator()

            self.text_zeros_tag = self.uuid("zeros_text")
            self.text_poles_tag = self.uuid("poles_text")

            dpg.add_text("Zeros:", color=[100, 100, 255])
            dpg.add_text("N/A", tag=self.text_zeros_tag)

            dpg.add_text("Poles:", color=[255, 100, 100])
            dpg.add_text("N/A", tag=self.text_poles_tag)

            self.symbolic_tf_tag = self.uuid("symbolic_tf")
            dpg.add_text("", tag=self.symbolic_tf_tag, color=[160, 200, 160], wrap=340)
            dpg.add_separator()

            with dpg.plot(label="S-Plane Map", width=350, height=350):
                dpg.add_plot_legend()
                x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Real Part, Sigma")
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Imaginary Part, jw")

                self.scatter_zeros_tag = self.uuid("scatter_zeros")
                self.scatter_poles_tag = self.uuid("scatter_poles")

                dpg.add_scatter_series([], [], label="Zeros", parent=y_axis, tag=self.scatter_zeros_tag)
                dpg.add_scatter_series([], [], label="Poles", parent=y_axis, tag=self.scatter_poles_tag)

                dpg.bind_item_theme(self.scatter_zeros_tag, self.create_scatter_theme(dpg.mvPlotMarker_Circle, [100, 100, 255, 255]))
                dpg.bind_item_theme(self.scatter_poles_tag, self.create_scatter_theme(dpg.mvPlotMarker_Cross, [255, 100, 100, 255]))

        super().build()

    def create_scatter_theme(self, marker_style, color_rgba):
        theme = dpg.add_theme()
        with dpg.theme_component(dpg.mvScatterSeries, parent=theme):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color_rgba, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, marker_style, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6, category=dpg.mvThemeCat_Plots)
        return theme

    def get_possible_node_connections(self) -> List[str]:
        return []

    # ------------------------------------------------------------------
    # [TR] Sayisal yol: descriptor (DAE) durum-uzayi + polinom ozdeger problemi.
    # [EN] Numeric path: descriptor (DAE) state-space form + polynomial
    #      eigenvalue problem.
    # ------------------------------------------------------------------

    def _extract_poly_coeffs(self, A_mat, s):
        """
        [TR] A(s)'in s'e gore polinom katsayi matrislerini cikarir:
             A(s) = A_0 + s*A_1 (+ olasi s^2*A_2, ...).
             Standart MNA endüktans/kondansator dallarini s*L / s*C olarak
             damgalar (1/(sL) degil), bu yuzden A(s) s'de TAM OLARAK AFINDIR:
             A_0 = A(s=0), A_1 = dA/ds - sonlu fark yok, kirpma yok.
             Bir eleman s'de rasyonel ise (ust-akista sembolik dugum indirgemesi)
             once tum matris ortak paydayla temizlenir; paydanin kokleri sahte
             (spurious) kok olarak dondurulur ve _filter_spurious_roots ile elenir.
             Doner: (np katsayi matrisleri listesi, max_derece, denom_lcm).

        [EN] Extract the polynomial coefficient matrices of A(s) in s:
             A(s) = A_0 + s*A_1 (+ possibly s^2*A_2, ...).
             Standard MNA stamps inductor/capacitor branches as s*L / s*C (not
             1/(sL)), so A(s) is EXACTLY affine in s: A_0 = A(s=0), A_1 = dA/ds
             - no finite differences, no truncation.
             If an entry is rational in s (an upstream symbolic node reduction),
             the whole matrix is first cleared by its least common denominator;
             the denominator roots are returned as spurious and dropped later by
             _filter_spurious_roots.
             Returns (list of np coefficient matrices, max_degree, denom_lcm).
        """
        n, m = A_mat.shape

        # [TR] Hizli yol: A(s) afinse (A_0 + s*A_1) tek turev + s=0 degeriyle
        #      dogrula ve eleman-bazli polinom taramasini atla.
        # [EN] Fast path: if A(s) is affine (A_0 + s*A_1), verify with one
        #      derivative + the value at s=0 and skip the per-entry scan.
        try:
            A0 = A_mat.subs(s, 0)
            A1 = A_mat.diff(s)
            if (A_mat - A0 - s * A1).applyfunc(sp.expand).is_zero_matrix:
                G_arr = np.array(A0, dtype=complex)
                if A1.is_zero_matrix:            # purely resistive: degree 0
                    return [G_arr], 0, sp.Integer(1)
                return [G_arr, np.array(A1, dtype=complex)], 1, sp.Integer(1)
        except Exception:
            pass

        non_poly_found = any(
            A_mat[i, j] != 0 and not A_mat[i, j].is_polynomial(s)
            for i in range(n) for j in range(m)
        )

        denom_lcm = sp.Integer(1)
        if non_poly_found:
            # [TR] Bir eleman s'de rasyonel: ortak payda ile temizle; payda
            #      kokleri sahte (spurious) kok olarak elenecek.
            # [EN] An entry is rational in s: clear by the common denominator;
            #      the denominator roots are dropped later as spurious.
            print("Uyari: A(s) matrisinde rasyonel (paydali) elemanlar tespit edildi; "
                  "ortak payda ile temizleniyor. Payda kokleri sahte (spurious) kok "
                  "olarak isaretlenip sonuclardan cikarilacak.", flush=True)
            for i in range(n):
                for j in range(m):
                    _, denom = sp.fraction(sp.together(A_mat[i, j]))
                    denom_lcm = sp.lcm(denom_lcm, denom)
            A_mat = sp.expand(A_mat * denom_lcm)

        max_deg = 0
        for i in range(n):
            for j in range(m):
                expr = A_mat[i, j]
                if expr == 0 or s not in expr.free_symbols:
                    continue
                try:
                    deg = sp.degree(expr, gen=s)
                except sp.PolynomialError:
                    continue
                if not deg.is_finite:
                    continue
                max_deg = max(max_deg, int(deg))

        coeff_mats_sym = [sp.zeros(n, m) for _ in range(max_deg + 1)]
        for i in range(n):
            for j in range(m):
                expr = A_mat[i, j]
                if expr == 0:
                    continue
                try:
                    poly = sp.Poly(expr, s)
                except sp.PolynomialError:
                    coeff_mats_sym[0][i, j] = expr.subs(s, 0)
                    continue
                asc_coeffs = poly.all_coeffs()[::-1]   # index d -> coeff of s^d
                for d, c in enumerate(asc_coeffs):
                    if d < len(coeff_mats_sym):
                        coeff_mats_sym[d][i, j] = c

        coeffs = [np.array(mat, dtype=complex) for mat in coeff_mats_sym]
        return coeffs, max_deg, denom_lcm

    def _compute_pencil_scaling(self, A_coeffs, k):
        """
        [TR] s = gamma * s_hat donusumu icin olcek katsayisi. Sabit terim A_0
             (direnc / dusuk frekans mertebesi) ile en yuksek dereceli terim
             A_k (jonksiyon kapasitesi / yuksek frekans mertebesi) s_hat ~ O(1)
             civarinda karsilastirilabilir olsun diye:
                 gamma = (||A_0|| / ||A_k||)^(1/k)   (k=1 icin ||G||/||C_dyn||).
             QZ adimindan once pencil'i sartlar.

        [EN] Scale factor for s = gamma * s_hat. Chosen so the constant term A_0
             (resistor / low-frequency scale) and the top-order term A_k
             (junction-capacitance / high-frequency scale) are comparable near
             s_hat ~ O(1):
                 gamma = (||A_0|| / ||A_k||)^(1/k)   (||G||/||C_dyn|| for k=1).
             This conditions the pencil before the QZ step.
        """
        norm_a0 = np.max(np.abs(A_coeffs[0])) if A_coeffs[0].size else 0.0
        norm_ak = np.max(np.abs(A_coeffs[k])) if A_coeffs[k].size else 0.0
        if norm_a0 > 0 and norm_ak > 0 and k > 0:
            gamma = (norm_a0 / norm_ak) ** (1.0 / k)
        else:
            gamma = 1.0
        return gamma

    def _equilibrate_pencil(self, A, B, iterations=2):
        """
        [TR] (A, B) matris demetini iki tarafli kosegen olceklemeyle dengeler:
             D*A*E, D*B*E (D, E kosegen ve tersinir). OZDEGERLERI DEGISTIRMEZ
             (ozvektorler v -> E^-1 v); sadece pF mertebesindeki jonksiyon
             kapasiteleriyle uF mertebesindeki kuplaj kapasiteleri ayni demette
             oldugunda QZ'nin sayisal kararliligini artirir.

        [EN] Balance the pencil (A, B) by two-sided diagonal scaling: D*A*E,
             D*B*E (D, E diagonal, invertible). This does NOT change the
             eigenvalues (eigenvectors map v -> E^-1 v); it only improves QZ
             stability when pF-range junction caps and uF-range coupling caps
             share one pencil.
        """
        n = A.shape[0]
        if n == 0:
            return A, B
        for _ in range(iterations):
            row_max = np.maximum(np.max(np.abs(A), axis=1), np.max(np.abs(B), axis=1))
            row_max[row_max == 0] = 1.0
            r = 1.0 / np.sqrt(row_max)
            A = A * r[:, None]
            B = B * r[:, None]

            col_max = np.maximum(np.max(np.abs(A), axis=0), np.max(np.abs(B), axis=0))
            col_max[col_max == 0] = 1.0
            c = 1.0 / np.sqrt(col_max)
            A = A * c[None, :]
            B = B * c[None, :]
        return A, B

    def _build_rosenbrock_coeffs(self, A_coeffs, B_coeffs, C_out, n):
        """
        [TR] Genellestirilmis Rosenbrock sistem-matrisi polinomunu kurar:
                 P(s) = [[A(s), -B(s)], [C_out, 0]]   ((n+1) x (n+1))
             Katsayi bazinda P_0 = [[G, -B_0], [C_out, 0]], P_i = [[A_i, -B_i], [0, 0]].
             B(s) de tam polinom olarak islenir cunku Norton kaynak donusumu
             (Vin/Z(s)) z'yi s'e bagli yapabilir. Schur tumleyeni ozdesligiyle
             det(P(s)) = det(A(s)) * C_out A(s)^-1 B(s), yani Cramer payi
             (iletim sifiri payi) ile BIREBIR aynidir - ama A(s)'in hicbir
             noktada tersinir olmasini gerektirmeyen tek bir ozdeger problemi.

        [EN] Build the generalized Rosenbrock system-matrix polynomial
                 P(s) = [[A(s), -B(s)], [C_out, 0]]   (size (n+1) x (n+1))
             coefficient-wise P_0 = [[G, -B_0], [C_out, 0]], P_i = [[A_i, -B_i], [0, 0]].
             B(s) is a full polynomial too, since a Norton source transform
             (Vin/Z(s)) can make z depend on s. By the Schur-complement identity
             det(P(s)) = det(A(s)) * C_out A(s)^-1 B(s) equals the Cramer
             numerator (the transmission-zero numerator) exactly - but as a
             single eigenproblem that never needs A(s) invertible.
        """
        k = max(len(A_coeffs), len(B_coeffs)) - 1
        m = n + 1
        P_coeffs = [np.zeros((m, m), dtype=complex) for _ in range(k + 1)]
        for i, Ai in enumerate(A_coeffs):
            P_coeffs[i][:n, :n] = Ai
        for i, Bi in enumerate(B_coeffs):
            P_coeffs[i][:n, n] = -Bi[:, 0]
        P_coeffs[0][n, :n] = C_out
        return P_coeffs, m, k

    def _solve_polynomial_eigenproblem(self, A_coeffs, n, k, gamma, abs_mag_limit=1e18):
        """
        [TR] Derece-k matris polinomu P(s) = sum_i s^i * A_coeffs[i] icin
             companion linearization ile kn x kn boyutlu genellestirilmis
             ozdeger problemi kurar ve scipy.linalg.eig (LAPACK ggev = QZ) ile
             cozer. k=1 durumunda bu tam olarak eig(A_0, -A_1) demektir.
             Sonsuz / sahte ozdegerler iki asamada elenir:
               1) GORECELI beta esigi (max|beta| * 1e-10): LAPACK'in (alpha,beta)
                  ciftleri girdi demetinin mutlak olcegiyle orantili oldugu icin
                  sabit bir esik gamma-olcekleme sonrasi yanlis olur.
               2) MUTLAK buyukluk siniri: gamma geri cevrilmis fiziksel deger
                  uzerinde - hicbir gercek devre kutbu/sifiri bunu asmaz.
             Sonlu ozdegerleri (fiziksel birimlerde) siralanmamis dondurur.

        [EN] For the degree-k matrix polynomial P(s) = sum_i s^i * A_coeffs[i],
             build a kn x kn generalized eigenproblem by companion linearization
             and solve it with scipy.linalg.eig (LAPACK ggev = the QZ algorithm).
             For k=1 this is exactly eig(A_0, -A_1). Infinite / spurious
             eigenvalues are removed in two stages:
               1) a RELATIVE beta threshold (max|beta| * 1e-10): LAPACK's
                  (alpha, beta) pairs scale with the absolute size of the input
                  pencil, so a fixed threshold would be wrong after gamma scaling.
               2) an ABSOLUTE magnitude cap on the gamma-undone physical value -
                  no real circuit pole/zero exceeds it.
             Returns the finite eigenvalues (physical units), unsorted.
        """
        if k == 0:
            return []

        N = n * k
        Acomp = np.zeros((N, N), dtype=complex)
        Bcomp = np.zeros((N, N), dtype=complex)

        for i in range(k - 1):
            Acomp[i*n:(i+1)*n, (i+1)*n:(i+2)*n] = np.eye(n)
        for i in range(k):
            Acomp[(k-1)*n:k*n, i*n:(i+1)*n] = -A_coeffs[i]

        for i in range(k - 1):
            Bcomp[i*n:(i+1)*n, i*n:(i+1)*n] = np.eye(n)
        Bcomp[(k-1)*n:k*n, (k-1)*n:k*n] = A_coeffs[k]

        Acomp, Bcomp = self._equilibrate_pencil(Acomp, Bcomp)

        alpha_beta = scipy.eig(Acomp, Bcomp, right=False, homogeneous_eigvals=True)
        alpha = alpha_beta[0, :]
        beta = alpha_beta[1, :]

        beta_tol = np.max(np.abs(beta)) * 1e-10 if beta.size else 0.0
        finite_mask = np.abs(beta) > beta_tol

        raw_eigs = (alpha[finite_mask] / beta[finite_mask]) * gamma

        clean = []
        for e in raw_eigs:
            if not (np.isfinite(e.real) and np.isfinite(e.imag)):
                continue
            if abs(e) > abs_mag_limit:
                continue
            clean.append(complex(e))
        return clean

    def _filter_spurious_roots(self, roots, denom_list, s, rel_tol=1e-6):
        """
        [TR] Rasyonel-eleman temizleme adiminda eklenen ortak-payda koklerini
             sonuclardan cikarir. A(s) ve z(s) ayri ayri paydali olabilecegi
             icin bir payda LISTESI alir. Tum paydalar 1 ise (her ikisi de saf
             polinom - normal durum) hicbir sey yapmaz.

        [EN] Remove the common-denominator roots introduced by the
             rational-entry clearing step. Takes a LIST of denominators because
             A(s) and z(s) may each be rational. If every denominator is 1
             (both pure polynomials - the normal case) it is a no-op.
        """
        spurious = []
        for denom in denom_list:
            if denom == 1:
                continue
            poly = sp.Poly(denom, s)
            if poly.degree() < 1:
                continue
            spurious.extend(np.roots([complex(sp.N(c)) for c in poly.all_coeffs()]))
        if not spurious:
            return roots
        clean = []
        for r in roots:
            if not any(abs(r - sr) < rel_tol * max(1.0, abs(sr)) for sr in spurious):
                clean.append(r)
        return clean

    def _resolve_output_node(self, mna_data):
        """
        [TR] Transfer fonksiyonunun cikis dugumu. KUTUPLAR cikis dugumunden
             BAGIMSIZDIR ama SIFIRLAR dogrudan ona baglidir; bir referans araca
             karsi karsilastirirken iki tarafta da AYNI dugum secili olmalidir.

        [EN] The output node of the transfer function. POLES are INDEPENDENT of
             the output node but ZEROS depend on it directly; when comparing
             against a reference tool the SAME node must be selected on both.
        """
        try:
            names = [str(u) for u in mna_data.get_unknowns()]
        except Exception as e:
            print(f"Bilinmeyenler okunamadi: {e}", flush=True)
            return None

        if self.src_output_node and self.src_output_node in names:
            return self.src_output_node

        chosen = names[-1] if names else None
        print(f"Cikis dugumu TransferFunction dugumunden alinamadi; gecici "
              f"olarak '{chosen}' kullaniliyor.", flush=True)
        print(f"Mevcut dugumler: {names}", flush=True)
        print("TransferFunction dugumunde cikis dugumunu secip Calculate'e basin.",
              flush=True)
        return chosen

    def _calculate_robust_poles_zeros(self, mna_data, unknown_variable: str):
        """
        [TR] Sayisal kutup/sifir cozumu (descriptor / DAE formulasyonu).

             MNA s'de tam afindir: A(s) = G + s*C_dyn.
             KUTUPLAR: det(G + s*C_dyn) = 0  <=>  eig(G, -C_dyn)
                       (k > 1 ise companion-linearized polinom ozdeger problemi).
             SIFIRLAR: A(s)'in cikis sutunu kaynak vektoru z ile degistirilir
                       (Cramer payi det(A_out(s))); (G_z, C_z) demetinin SONLU
                       ozdegerleri = sifirlar. scipy.linalg.eig dogrudan cagrilir
                       ve TUM sonlu ozdegerler tutulur (goreceli beta esigi
                       uygulanmaz), boylece cok yuksek frekansli sifirlar da gelir.
             pF/uF olcek farki icin gamma-olcekleme + satir/sutun dengeleme.
             Sonuc buyuklugüne gore sirali dondurulur.

        [EN] Numeric pole/zero solve (descriptor / DAE formulation).

             MNA is exactly affine in s: A(s) = G + s*C_dyn.
             POLES: det(G + s*C_dyn) = 0  <=>  eig(G, -C_dyn)
                    (companion-linearized polynomial eigenproblem for k > 1).
             ZEROS: replace the output column of A(s) with the source vector z
                    (Cramer numerator det(A_out(s))); the FINITE eigenvalues of
                    the pencil (G_z, C_z) are the zeros. scipy.linalg.eig is
                    called directly and ALL finite eigenvalues are kept (no
                    relative beta threshold), so very-high-frequency zeros
                    survive.
             gamma scaling + row/column equilibration for the pF/uF spread.
             Result sorted by magnitude.
        """
        s = sp.symbols('s')
        unknown_variable_symbol = sp.symbols(unknown_variable)
        if unknown_variable_symbol not in mna_data.unknowns:
            raise ValueError(f"Bilinmeyen değişken {unknown_variable} sistemde yok.")

        x_syms = list(mna_data.get_unknowns())
        idx_out = x_syms.index(unknown_variable_symbol)

        A_sym = mna_data.A.subs(mna_data.value_dict)
        z_sym = mna_data.z.subs(mna_data.value_dict)
        n = A_sym.shape[0]

        try:
            # A(s) = G + s*C_dyn (+ possible higher orders)
            A_coeffs, k, denom_lcm = self._extract_poly_coeffs(A_sym, s)
            G = A_coeffs[0]
            C_dyn = A_coeffs[1] if k >= 1 else np.zeros_like(G)
            cond_g = np.linalg.cond(G) if G.size else 0.0
            norm_g = np.max(np.abs(G)) if G.size else 0.0
            dyn_range = (np.max(np.abs(C_dyn)) / norm_g) if norm_g > 0 else 0.0
            print(f"Tespit edilen A(s) polinom derecesi: k={k}"
                  + (" (afin/birinci derece descriptor DAE: A(s)=G+s*C_dyn, kirpma yok)"
                     if k <= 1 else
                     " (yuksek dereceli dinamik tespit edildi - tam PEP cozumu uygulaniyor)")
                  + f" | cond(G)={cond_g:.3e} | ||C_dyn||/||G||={dyn_range:.3e}",
                  flush=True)

            # [TR] z kaynak vektorunu de tam polinom olarak cikar (Norton
            #      donusumu z'yi s'e bagli yapabilir).
            # [EN] Extract z as a full polynomial too (a Norton transform can
            #      make z depend on s).
            B_coeffs, k_z, denom_lcm_z = self._extract_poly_coeffs(z_sym, s)
            if k_z > 0:
                print(f"NOT: z(s) kaynak vektoru s'e BAGLI (derece {k_z}); "
                      f"tam polinom olarak kullaniliyor.", flush=True)

            # [TR] C_out'u G mertebesine olcekle: KOKLERI DEGISTIRMEZ, sadece
            #      Rosenbrock demetinin son satirini diger satirlarla ayni
            #      buyukluk mertebesinde tutar.
            # [EN] Scale C_out to the size of G: does NOT change the roots, it
            #      just keeps the Rosenbrock pencil's last row at the same
            #      magnitude as the others.
            c_scale = norm_g if norm_g > 0 else 1.0
            C_out = np.zeros((1, n), dtype=complex)
            if 0 <= idx_out < n:
                C_out[0, idx_out] = c_scale

            # POLES: descriptor pencil eigenproblem
            gamma_A = self._compute_pencil_scaling(A_coeffs, k)
            A_scaled = [(gamma_A ** i) * A_coeffs[i] for i in range(k + 1)]
            poles_num = self._solve_polynomial_eigenproblem(A_scaled, n, k, gamma_A)
            poles_num = self._filter_spurious_roots(poles_num, [denom_lcm], s)
            # [TR] (|z|, Re, Im) ile sirala: sadece |z| eslenik ciftleri ayirt edemez.
            # [EN] sort by (|z|, Re, Im): |z| alone cannot separate conjugates.
            poles_num = sorted(poles_num, key=lambda v: (abs(v), v.real, v.imag))

            # ZEROS
            if k == 1 and k_z <= 1:
                # [TR] Cikis sutununu z ile degistir; (G_z, C_z) demetinin sonlu
                #      ozdegerleri = sifirlar. Tum sonlu ozdegerler tutulur.
                # [EN] Replace the output column with z; the finite eigenvalues
                #      of (G_z, C_z) are the zeros. All finite eigenvalues kept.
                Gz = A_coeffs[0].copy()
                Cz = A_coeffs[1].copy()
                Gz[:, idx_out] = B_coeffs[0][:, 0]
                Cz[:, idx_out] = B_coeffs[1][:, 0] if k_z >= 1 else 0.0
                Gz_eq, Cz_eq = self._equilibrate_pencil(Gz, -Cz)
                ev = scipy.eig(Gz_eq, Cz_eq, right=False)
                zeros_num = [complex(e) for e in ev
                             if np.isfinite(e.real) and np.isfinite(e.imag)]
            else:
                # [TR] Yuksek dereceli / s'e bagli kaynak: Rosenbrock sistem
                #      matrisi P(s) = [[A(s), -B(s)], [C_out, 0]].
                # [EN] Higher order / s-dependent source: Rosenbrock system
                #      matrix P(s) = [[A(s), -B(s)], [C_out, 0]].
                P_coeffs, m, k_P = self._build_rosenbrock_coeffs(
                    A_coeffs, B_coeffs, C_out, n)
                gamma_P = self._compute_pencil_scaling(P_coeffs, k_P)
                P_scaled = [(gamma_P ** i) * P_coeffs[i] for i in range(k_P + 1)]
                zeros_num = self._solve_polynomial_eigenproblem(P_scaled, m, k_P, gamma_P)

            zeros_num = self._filter_spurious_roots(zeros_num, [denom_lcm, denom_lcm_z], s)
            zeros_num = sorted(zeros_num, key=lambda v: (abs(v), v.real, v.imag))

        except Exception as e:
            print(f"Nümerik PEP Çözümleme Hatası: {e}", flush=True)
            zeros_num = []
            poles_num = []

        return {"zeros": zeros_num, "poles": poles_num}

    # ------------------------------------------------------------------
    # [TR] Sembolik yol: H(s) = det(A_out(s)) / det(A(s)) tam rasyonel olarak.
    # [EN] Symbolic path: H(s) = det(A_out(s)) / det(A(s)) as an exact rational.
    # ------------------------------------------------------------------
    def _to_exact(self, v):
        """
        [TR] float -> tam rasyonel. repr(float) round-trip eden en kisa
             ondaligi verdigi icin Rational(repr(x)) amaclanan degeri
             (or. 1e-9 kapasite) tam yakalar.
        [EN] float -> exact rational. repr(float) is the shortest round-tripping
             decimal, so Rational(repr(x)) captures the intended value
             (e.g. a 1e-9 capacitance) exactly.
        """
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            raise ValueError(f"deger sonlu degil: {v!r}")
        try:
            return sp.Rational(repr(f))
        except (ValueError, TypeError):
            return sp.nsimplify(f, rational=True)

    def _roots_of_exact_poly(self, poly, s):
        """
        [TR] Tam katsayili polinomun kokleri. Once sondaki sifir katsayilar
             sayilarak s = 0 kokleri TAM alinir (kuplaj kondansatorleri), sonra
             rasyonel / kat kokler (sp.roots), en son kalanlar sayisal
             (nroots, 25 basamak).
        [EN] Roots of an exact-coefficient polynomial. First the trailing zero
             coefficients are counted to take the s = 0 roots EXACTLY (coupling
             caps), then rational / repeated roots (sp.roots), then the rest
             numerically (nroots, 25 digits).
        """
        if poly is None or poly.total_degree() < 1:
            return []
        coeffs = poly.all_coeffs()   # highest degree first
        mult0 = 0
        for c in reversed(coeffs):
            if c == 0:
                mult0 += 1
            else:
                break
        out = [complex(0.0, 0.0)] * mult0
        rest = coeffs[:len(coeffs) - mult0] if mult0 else coeffs
        if len(rest) >= 2:
            deflated = sp.Poly(rest, s)
            try:
                rd = sp.roots(deflated)
                if rd and sum(rd.values()) == deflated.degree():
                    for r, mult in rd.items():
                        out.extend([complex(r)] * mult)
                    return out
            except Exception:
                pass
            for r in deflated.nroots(n=25, maxsteps=500):
                out.append(complex(r))
        return out

    def _det_poly(self, M, s):
        """
        [TR] det(M(s))'i s cinsinden tam bir POLINOM olarak dondurur (arayan
             fonksiyon 1/s paydalarini onceden temizler, bkz. _clear_s_denoms).
             M'nin her elemani s'de en fazla d. dereceden ise det(M) en fazla
             n*d. derecedendir. Sembolik acilim yerine: M'yi n*d+1 farkli tam
             rasyonel s degerinde degerlendir (her biri bolmesiz, saf rasyonel
             bir Bareiss determinanti), sonra Lagrange ile geri kur. Tum
             aritmetik tam rasyoneldir; fazladan bir noktada dogrulanir.
             Interpolasyon tutmazsa berkowitz + sp.cancel'e doner.

        [EN] Return det(M(s)) as an exact POLYNOMIAL in s (the caller clears any
             1/s denominators first, see _clear_s_denoms). If every entry of M
             is degree <= d in s, det(M) is degree <= n*d. Instead of a symbolic
             expansion: evaluate M at n*d+1 distinct exact rational values of s
             (each a fraction-free pure-rational Bareiss determinant), then
             rebuild by Lagrange interpolation. All arithmetic is exact
             rational; verified at one extra point. On mismatch it falls back to
             berkowitz + sp.cancel.
        """
        n = M.shape[0]
        try:
            deg = 1
            for i in range(n):
                for j in range(n):
                    e = M[i, j]
                    if e != 0 and e.has(s):
                        try:
                            deg = max(deg, int(sp.degree(e, s)))
                        except (sp.PolynomialError, TypeError):
                            deg = max(deg, 1)
            npts = n * deg + 1
            pts = [sp.Rational(2 * i + 1, 7) for i in range(npts)]
            ys = [M.xreplace({s: p}).det(method="bareiss") for p in pts]
            cand = sp.Poly(sp.interpolate(list(zip(pts, ys)), s), s)
            check = sp.Rational(3, 5)
            if M.xreplace({s: check}).det(method="bareiss") == cand.eval(check):
                return cand.as_expr()
        except Exception:
            pass
        return sp.cancel(M.det(method="berkowitz"))

    @staticmethod
    def _clear_s_denoms(A, A_out, s):
        """
        [TR] Enduktanslar MNA'da 1/(s*L) olarak damgalanir, dolayisiyla A(s)
             s'de RASYONELdir - oysa _det_poly interpolasyonu polinom bekler.
             Her iki matrisi de s^k ile carp (k = herhangi bir elemanin
             paydasindaki en yuksek s kuvveti). det(s^k * M) = s^(k*n) * det(M)
             oldugundan bu ortak carpan H = det(A_out)/det(A) oraninda TAM
             sadelesir; ama matrisler artik polinom -> hizli interpolasyon.
             1/s yoksa (yalniz R/C) matrisler dokunulmadan geri doner.

        [EN] Inductors are stamped as 1/(s*L) in the MNA, so A(s) is RATIONAL in
             s - but the _det_poly interpolation expects a polynomial. Multiply
             both matrices by s^k (k = the highest power of s in any entry's
             denominator). det(s^k * M) = s^(k*n) * det(M), so this common
             factor cancels EXACTLY in H = det(A_out)/det(A); the matrices are
             now polynomial -> fast interpolation. With no 1/s (pure R/C) the
             matrices are returned untouched.
        """
        n = A.shape[0]
        k = 0
        for i in range(n):
            for j in range(n):
                e = A[i, j]
                if e != 0 and e.has(s):
                    den = sp.together(e).as_numer_denom()[1]
                    if den.has(s):
                        try:
                            k = max(k, int(sp.degree(den, s)))
                        except (sp.PolynomialError, TypeError):
                            k = max(k, 1)
        if k == 0:
            return A, A_out
        mult = s ** k
        return ((A * mult).applyfunc(sp.expand),
                (A_out * mult).applyfunc(sp.expand))

    def _calculate_symbolic_poles_zeros(self, mna_data, unknown_variable: str):
        """
        [TR] Sembolik (kapali-form) kutup/sifir cozumu.

             Cramer kurali:  H(s) = V_out(s) / U_in(s) = det(A_out(s)) / det(A(s))
             - A_out = A'nin cikis sutunu kaynak vektoru z ile degistirilmis hali
             - KUTUPLAR = det(A) = 0 kokleri
             - SIFIRLAR = det(A_out) = 0 kokleri (ortak carpanlar sadelestikten sonra)
             Eleman degerleri tam rasyonele cevrilir. s = 0'daki kutup/sifirlar
             (kuplaj kondansatorleri) pay/paydada tam s^k carpani olarak cikar -
             sayisal QZ'deki "~1e-8" tozu olmaz. Ayrica carpanlarina ayrilmis
             H(s) metni dondurur. Basarisizlikta sayisal yola donulur.

        [EN] Symbolic (closed-form) pole/zero solve.

             Cramer's rule:  H(s) = V_out(s) / U_in(s) = det(A_out(s)) / det(A(s))
             - A_out = A with its output column replaced by the source vector z
             - POLES = roots of det(A) = 0
             - ZEROS = roots of det(A_out) = 0 (after common factors cancel)
             Element values are converted to exact rationals. The s = 0
             poles/zeros (coupling caps) appear as an exact s^k factor - no
             "~1e-8" dust like the numeric QZ path. Also returns a factored H(s)
             string. Falls back to the numeric path on failure.
        """
        s = sp.symbols('s')
        x_syms = [str(u) for u in mna_data.get_unknowns()]
        if unknown_variable not in x_syms:
            raise ValueError(f"'{unknown_variable}' bilinmeyenler arasinda yok.")
        idx_out = x_syms.index(unknown_variable)

        vd = {k: self._to_exact(v) for k, v in mna_data.value_dict.items()}
        A = sp.Matrix(mna_data.A).xreplace(vd)
        z = sp.Matrix(mna_data.z).xreplace(vd)
        n = A.shape[0]
        if n > 24:
            print(f"UYARI: {n}x{n} sembolik determinant - bu biraz surebilir.",
                  flush=True)

        # [TR] A yalnizca s'e bagli olmali; cozulememis bir eleman sembolu
        #      kalmissa sembolik yol anlamsiz -> sayisal yola don.
        # [EN] A must depend only on s; if an unresolved element symbol remains
        #      the symbolic path is meaningless -> fall back to numeric.
        extra = A.free_symbols - {s}
        if extra:
            raise ValueError(f"MNA matrisinde cozulememis sembol(ler): "
                             f"{', '.join(map(str, extra))}")

        A_out = A.copy()
        A_out[:, idx_out] = z

        # [TR] Enduktansli devrelerde A(s) 1/(s*L) yuzunden s'de rasyoneldir;
        #      iki matrisi de s^k ile carparak polinom yap (ortak s^(k*n)
        #      carpani D_expr/N_expr oraninda sadelesir). Boylece _det_poly
        #      interpolasyonu calisir ve berkowitz'in n>=10'da takilmasi onlenir.
        # [EN] With inductors A(s) is rational in s (1/(s*L)); make both matrices
        #      polynomial by multiplying by s^k (the shared s^(k*n) factor
        #      cancels in D_expr/N_expr). This lets the _det_poly interpolation
        #      run instead of berkowitz stalling for n >= 10.
        A, A_out = self._clear_s_denoms(A, A_out, s)

        D_expr = self._det_poly(A, s)
        N_expr = self._det_poly(A_out, s)

        if D_expr == 0 or D_expr.has(sp.nan, sp.zoo, sp.oo) \
                or N_expr.has(sp.nan, sp.zoo, sp.oo):
            raise ValueError("sembolik determinant tekil / tanimsiz "
                             "(D=0 veya nan) - sayisal yola donuluyor")

        # [TR] Ortak (s-bagimli) carpanlari sadelestir. det'ler enduktansli
        #      devrelerde rasyonel olabilecegi icin once together/cancel.
        # [EN] Cancel common (s-dependent) factors. The determinants can be
        #      rational (inductor circuits), so together/cancel first.
        H = sp.cancel(sp.together(N_expr / D_expr))
        N2, D2 = sp.fraction(H)
        p_poly = sp.Poly(D2, s)
        z_poly = sp.Poly(N2, s)

        poles = sorted(self._roots_of_exact_poly(p_poly, s),
                       key=lambda v: (abs(v), v.real, v.imag))
        zeros = sorted(self._roots_of_exact_poly(z_poly, s),
                       key=lambda v: (abs(v), v.real, v.imag))

        tf_string = self._factored_tf_string(zeros, poles, z_poly, p_poly, s)
        print(f"Sembolik: pay derecesi {z_poly.degree()}, "
              f"payda derecesi {p_poly.degree()}.", flush=True)
        print(tf_string, flush=True)
        return {"zeros": zeros, "poles": poles, "tf_string": tf_string}

    def _factored_tf_string(self, zeros, poles, z_poly, p_poly, s) -> str:
        """
        [TR] H(s)'i carpanlarina ayrilmis, okunabilir bicimde yazar:
                 H(s) = K * s^k (s + a)(s^2 + b s + c) / [ (s + p1)(s + p2) ... ]
             s = 0 kokleri tam 0 oldugu icin s^k carpani net gorunur; eslenik
             ciftler (s^2 + b s + c) olarak toplanir; kazanc K = z_poly.LC() / p_poly.LC().
        [EN] Render H(s) in a readable factored form:
                 H(s) = K * s^k (s + a)(s^2 + b s + c) / [ (s + p1)(s + p2) ... ]
             The s = 0 roots are exactly 0 so the s^k factor is clean; conjugate
             pairs are grouped as (s^2 + b s + c); the gain is
             K = z_poly.LC() / p_poly.LC().
        """
        def group(roots):
            origin = sum(1 for r in roots if r == 0)
            rest = [r for r in roots if r != 0]
            parts = []
            if origin:
                parts.append("s" if origin == 1 else f"s^{origin}")
            used = [False] * len(rest)
            for i, r in enumerate(rest):
                if used[i]:
                    continue
                if abs(r.imag) <= 1e-6 * abs(r.real):
                    # [TR] r koku -> carpan (s - r).  [EN] root r -> factor (s - r).
                    sign = "-" if r.real >= 0 else "+"
                    parts.append(f"(s {sign} {abs(r.real):.4g})")
                    used[i] = True
                    continue
                for j in range(i + 1, len(rest)):
                    if not used[j] and abs(rest[j] - r.conjugate()) <= 1e-6 * abs(r):
                        used[i] = used[j] = True
                        b, c = -2.0 * r.real, abs(r) ** 2
                        bs = "+" if b >= 0 else "-"
                        parts.append(f"(s^2 {bs} {abs(b):.4g} s + {c:.4g})")
                        break
                else:
                    used[i] = True
                    parts.append(f"(s - ({r.real:.4g}{r.imag:+.4g}j))")
            return " ".join(parts) if parts else "1"

        try:
            K = complex(z_poly.LC()) / complex(p_poly.LC())
            k_str = (f"{K.real:.4g}" if abs(K.imag) <= 1e-9 * abs(K.real)
                     else f"{K:.4g}")
        except Exception:
            k_str = "K"
        return (f"H(s) = {k_str} * {group(zeros)}\n"
                f"       / [ {group(poles)} ]")

    def _extract_mna(self, raw, build_from_circuit: bool = True):
        data = raw
        if isinstance(data, tuple):
            picked = None
            for item in data:
                if hasattr(item, "mna"):
                    picked = item.mna
                    break
                if hasattr(item, "A") and hasattr(item, "z"):
                    picked = item
                    break
            data = picked if picked is not None else (data[0] if data else None)
        if hasattr(data, "mna"):
            data = data.mna
        if (build_from_circuit and data is not None and not hasattr(data, "A")
                and hasattr(data, "elements")):
            from Modified_Node_Analysis import ModifiedNodalAnalysis
            mna = ModifiedNodalAnalysis(data)
            mna.buildEquationsSystem()
            data = mna
        if data is not None and hasattr(data, "A") and hasattr(data, "z"):
            return data
        return None

    def _read_link_context(self, raw):
        mode, out_node = "", ""
        if (isinstance(raw, (tuple, list)) and len(raw) >= 5
                and hasattr(raw[2], "A") and hasattr(raw[2], "z")):
            m, on = raw[3], raw[4]
            if isinstance(m, str):
                mode = m
            if isinstance(on, str):
                out_node = on
        return self._extract_mna(raw), mode, out_node

    def _update_source_info(self):
        if not (self.source_info_tag and dpg.does_item_exist(self.source_info_tag)):
            return
        if self.src_mode:
            label = {"numeric": "TF Numeric (QZ / sayisal)",
                     "symbolic": "TF Symbolic (det N(s)/D(s))"}.get(
                        self.src_mode, self.src_mode)
            node = self.src_output_node or "(TF dugumunde secilmedi)"
            dpg.set_value(self.source_info_tag,
                          f"Kaynak: {label}\nCikis dugumu: {node}")
        else:
            dpg.set_value(self.source_info_tag,
                          "Kaynak: bir TransferFunction dugumu baglayin "
                          "(veya dogrudan MNA).")

    def onlink_callback(self):
        try:
            raw = self.get_input_pin_value("mna_pin")
            _, mode, out_node = self._read_link_context(raw)
            self.src_mode = mode
            self.src_output_node = out_node
            self._update_source_info()
        except Exception as e:
            print(f"Kaynak baglami okunamadi: {e}", flush=True)
        super().onlink_callback()

    def calculate_callback(self, sender, app_data, user_data=None):
        raw = self.get_input_pin_value("mna_pin")

        print("\n--- POLE/ZERO HESAPLAMA TETİKLENDİ ---", flush=True)
        print(f"Kablodan Gelen İlk Veri Tipi: {type(raw)}", flush=True)

        try:
            mna_data, mode, out_node = self._read_link_context(raw)
            if mode:
                self.src_mode = mode
            if out_node:
                self.src_output_node = out_node
            self._update_source_info()
        except Exception as e:
            import traceback
            traceback.print_exc()
            dpg.set_value(self.text_zeros_tag, "MNA kurulamadi!")
            dpg.set_value(self.text_poles_tag, str(e))
            return

        if not mna_data or not hasattr(mna_data, 'A') or not hasattr(mna_data, 'z'):
            hata_msj = type(mna_data).__name__ if mna_data else "None (Veri Yok)"
            print(f"Hata: Beklenen özellikler bulunamadı! Mevcut obje: {hata_msj}", flush=True)
            dpg.set_value(self.text_zeros_tag, f"Error: Received {hata_msj}")
            dpg.set_value(self.text_poles_tag, "Valid MNA object not found.")
            return

        try:
            target_node = self._resolve_output_node(mna_data)
            if not target_node:
                dpg.set_value(self.text_zeros_tag, "Output node secilemedi.")
                dpg.set_value(self.text_poles_tag, "MNA bilinmeyenleri okunamadi.")
                return
            symbolic_mode = (self.src_mode == "symbolic")
            print(f"Hedef düğüm ({target_node}) için hesaplama yapılıyor "
                  f"[{'sembolik' if symbolic_mode else 'sayisal QZ'} yol]...",
                  flush=True)

            pz_results = None
            if symbolic_mode:
                print("TF Symbolic'ten geldi; H(s) tam rasyonel olarak "
                      "cozuluyor (buyuk devrelerde yavas olabilir)...", flush=True)
                try:
                    pz_results = self._calculate_symbolic_poles_zeros(
                        mna_data, target_node)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"Sembolik cozum basarisiz ({e}); sayisal QZ yoluna "
                          f"donuluyor.", flush=True)

            if pz_results is None:
                pz_results = self._calculate_robust_poles_zeros(mna_data, target_node)

            self.zeros = pz_results["zeros"]
            self.poles = pz_results["poles"]

            z_str = "\n".join([f"{z:.2e}" for z in self.zeros]) if self.zeros else "No Zeros"
            p_str = "\n".join([f"{p:.2e}" for p in self.poles]) if self.poles else "No Poles"

            dpg.set_value(self.text_zeros_tag, z_str)
            dpg.set_value(self.text_poles_tag, p_str)

            if self.symbolic_tf_tag and dpg.does_item_exist(self.symbolic_tf_tag):
                dpg.set_value(self.symbolic_tf_tag, pz_results.get("tf_string", ""))

            z_real = [float(z.real) for z in self.zeros]
            z_imag = [float(z.imag) for z in self.zeros]
            p_real = [float(p.real) for p in self.poles]
            p_imag = [float(p.imag) for p in self.poles]

            dpg.configure_item(self.scatter_zeros_tag, x=z_real, y=z_imag)
            dpg.configure_item(self.scatter_poles_tag, x=p_real, y=p_imag)

            y_axis_id = dpg.get_item_parent(self.scatter_zeros_tag)
            plot_id = dpg.get_item_parent(y_axis_id)
            children = dpg.get_item_children(plot_id, slot=1)   # slot 1 = axes
            if children and len(children) >= 2:
                x_axis_id = children[0]
                y_axis_id = children[1]
                dpg.fit_axis_data(x_axis_id)
                dpg.fit_axis_data(y_axis_id)

            print("Çizim başarıyla tamamlandı ve eksenler fit edildi!", flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            dpg.set_value(self.text_zeros_tag, "Computation Error!")
            dpg.set_value(self.text_poles_tag, str(e))
