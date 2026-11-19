# Normale Sparse-Tableau-Analyse (STA)
### Werkzeug zur symbolischen Netzwerkanalyse — Präsentationsunterlage

**Datei:** `Sparse_Tableau_Normal.py` · **Klasse:** `SparseTableauNormal`

---

## Ablauf der Präsentation

1. Theorie und Mathematik → **Teil 1**
2. Kurzfassung des Algorithmus → **Teil 2**
3. Tabelle der Funktionsblöcke → **Teil 3**
4. Funktion für Funktion: Aufgabe + mathematische Entsprechung + Code → **Teil 4**
5. Vollständig durchgerechnetes Beispiel → **Teil 5**
6. Verifikation, Fragen, Glossar → **Teil 6–8**

---
---

# TEIL 1 — THEORIE

## 1.1 Worum geht es?

Alles, was man über ein Netzwerk wissen will, besteht aus zwei Größen: **der Spannung jedes
Zweiges** und **dem Strom jedes Zweiges**. Klassische Verfahren (Knotenanalyse, MNA)
eliminieren die meisten dieser Größen von Hand und erhalten ein kleines System.

**Die Sparse-Tableau-Analyse macht genau das Gegenteil: sie eliminiert nichts.**

$$ x = [\, u_1 \; u_2 \; \dots \; u_b \mid i_1 \; i_2 \; \dots \; i_b \,]^T $$

`b` = Anzahl der Zweige. Zahl der Unbekannten: **2b**. Die Elimination übernimmt nicht der
Mensch, sondern der LU-Löser.

**Der Vorteil:** die Matrix ist dünnbesetzt (sparse), sie enthält keine Brüche, und jede Zeile
entspricht genau einem physikalischen Gesetz. Man kann also auf die Matrix schauen und sagen:
„diese Zeile ist die Gleichung von R1".

| | MNA | Normale STA |
|---|---|---|
| Unbekannte | Knotenpotentiale + einige Ströme | ausschließlich `u` und `i` |
| Größe | ~n (klein) | 2b (groß) |
| Besetzung | dicht | **dünnbesetzt** |
| Widerstand | Division `1/R` nötig | `R·i − u = 0`, keine Division |
| Zeile ↔ Element | viele-zu-viele | **eins-zu-eins** |

---

## 1.2 Graphentheoretische Grundlage

Das Netzwerk wird auf einen Graphen reduziert: Knoten = Ecken, Elemente = Kanten.

- `n` = Anzahl der Knoten (Masse eingeschlossen)
- `b` = Anzahl der Zweige
- **Spannbaum (aufspannender Baum):** eine Teilmenge der Zweige ohne Schleifen, die alle
  Knoten erreicht

Zwei Grundzahlen:

$$ \text{Anzahl Baumzweige} = n - 1 \qquad\qquad \text{Anzahl Verbindungszweige} \;=\; l = b - (n-1) $$

Daraus ergibt sich das **Gleichungsbudget**:

| Gleichungsgruppe | Anzahl | Matrixform | Herkunft |
|---|---|---|---|
| KCL — Knotensatz | `n − 1` | `A·i = 0` | Stromerhaltung an jedem Knoten |
| KVL — Maschensatz | `l = b − n + 1` | `B·u = 0` | Spannungserhaltung in jeder unabhängigen Masche |
| Bauelementgleichungen | `b` | `Q·u + P·i = s` | die Physik jedes einzelnen Elements |
| **SUMME** | **2b** | | ✔ gleich der Zahl der Unbekannten |

> **In der Präsentation betonen:** dass die Zahl der Gleichungen genau der Zahl der
> Unbekannten entspricht, ist kein Zufall, sondern eine Garantie der Graphentheorie:
> `(n−1) + (b−n+1) + b = 2b`.

**Entsprechung im Code:** `self.n = len(node_map) - 1` (also **n−1**), `self.m = b`,
`self.l = self.m - self.n`.
Achtung: `self.n` im Code ist nicht das `n` der Vorlesung, sondern `n−1` — weil die Massezeile
ohnehin gestrichen wird.

---

## 1.3 Blockstruktur des Systems

```
          u  (b Spalten)    i  (b Spalten)
        ┌──────────────┬──────────────┐  ┌───┐     ┌───┐
 KVL    │      B       │      0       │  │ u │     │ 0 │   ← l Zeilen
        ├──────────────┼──────────────┤  │   │     ├───┤
 KCL    │      0       │      A       │  │   │  =  │ 0 │   ← (n−1) Zeilen
        ├──────────────┼──────────────┤  │ i │     ├───┤
 Element│      Q       │      P       │  │   │     │ s │   ← b Zeilen
        └──────────────┴──────────────┘  └───┘     └───┘
                  T  (2b × 2b)              x        RHS
```

**Warum ist der obere Teil der rechten Seite null?** Weil die Kirchhoffschen Gesetze
**homogen** sind — sie erzwingen nichts, sie schränken nur ein. Angeregt wird das Netzwerk
allein durch die unabhängigen Quellen, und die erscheinen ausschließlich im Vektor `s`.

**Warum diese Reihenfolge (erst u dann i, erst KVL dann KCL)?** Damit sich das Tableau Zeile
für Zeile und Spalte für Spalte mit `SparseTableau.m` von Analog Insydes vergleichen lässt.
Eine andere Reihenfolge liefert ein ebenso korrektes System, aber die Ausgaben wären nicht
mehr direkt vergleichbar.

---

## 1.4 Block A — reduzierte Inzidenzmatrix (KCL)

$$
A[k,j] =
\begin{cases}
+1 & \text{wenn Zweig } j \text{ den Knoten } k \text{ verlässt} \\
-1 & \text{wenn Zweig } j \text{ in den Knoten } k \text{ eintritt} \\
\;\;0 & \text{wenn Zweig } j \text{ den Knoten } k \text{ nicht berührt}
\end{cases}
$$

Die `k`-te Zeile von `A·i = 0` besagt: *„die Summe der aus Knoten k herausfließenden Ströme
ist null"* — das ist der Knotensatz.

**Warum wird die Massezeile gestrichen?**
Addiert man alle Zeilen der vollständigen Inzidenzmatrix, erhält man den Nullvektor — die
Zeilen sind also linear abhängig, der Rang ist `n−1`. Eine Zeile zu streichen bedeutet in der
Sprache der Matrizen: **einen Bezugsknoten wählen**. Gestrichen wird die Zeile der Masse; das
ist die algebraische Entsprechung von „Masse = 0 V".

---

## 1.5 Block B — Fundamentalmaschenmatrix (KVL)

Der klassische Zugang lautet „Maschen durch Hinsehen finden". Am Rechner geht das nicht,
deshalb gehen wir **algebraisch** vor. Drei Schritte:

**Schritt 1 — den Baum an der Masse verwurzeln.** Im Baum ist der Weg zu jedem Knoten
**eindeutig** (keine Schleifen). Also lässt sich jedes Knotenpotential als vorzeichenbehaftete
Summe der Baumzweigspannungen entlang dieses Weges schreiben:

$$ e_k \;=\; \sum_{j \in \text{Weg}(0 \to k)} c_{kj}\, u_j $$

Vorzeichenregel: wegen `u_j = e_p − e_n` gilt
- Gang von p nach n: `e_n = e_p − u_j` → Koeffizient **−1**
- Gang von n nach p: `e_p = e_n + u_j` → Koeffizient **+1**

**Schritt 2 — jeder Verbindungszweig schließt genau eine unabhängige Masche.** Für diesen
Zweig gilt:

$$ u_{\text{link}} \;=\; e_p - e_n $$

**Schritt 3 — umstellen, so entsteht die Maschengleichung:**

$$ \boxed{\;u_{\text{link}} \;-\; \big(c_p - c_n\big)\cdot u \;=\; 0\;} $$

Diese Zeile ist unmittelbar die `k`-te Zeile von `B`: `+1` in der eigenen Spalte des
Verbindungszweiges, `∓`-Koeffizienten in den Spalten der Baumzweige des Weges.

**Goldene Regel / Test:** es gilt stets

$$ A \cdot B^T = 0 $$

(Tellegen-Orthogonalität). Das ist der schnellste Weg zu prüfen, ob die Topologie im Code
stimmt.

---

## 1.6 Blöcke P, Q, s — Bauelementgleichungen

Für jeden Zweig `j` genau **eine** Zeile:

$$ P[j,:]\cdot i \;+\; Q[j,:]\cdot u \;=\; s[j] $$

| Element | Gleichung | Eintrag in P | Eintrag in Q | Eintrag in s |
|---|---|---|---|---|
| Widerstand **R** | `R·i − u = 0` | `P[j,j] = R` | `Q[j,j] = −1` | 0 |
| Spule **L** | `sL·i − u = 0` | `P[j,j] = sL` | `Q[j,j] = −1` | 0 |
| Kondensator **C** | `sC·u − i = 0` | `P[j,j] = −1` | `Q[j,j] = sC` | 0 |
| Spannungsquelle **V** | `u = V` | — | `Q[j,j] = 1` | `V` |
| Stromquelle **I** | `i = I` | `P[j,j] = 1` | — | `I` |
| **E** (VCVS) | `μ·u_ctrl − u_out = 0` | — | `Q[j,j] = −1`, `Q[j,ctrl] = μ` | 0 |
| **G** (VCCS) | `gm·u_ctrl − i_out = 0` | `P[j,j] = −1` | `Q[j,ctrl] = gm` | 0 |
| **F** (CCCS) | `β·i_ctrl − i_out = 0` | `P[j,j] = −1`, `P[j,ctrl] = β` | — | 0 |
| **H** (CCVS) | `rm·i_ctrl − u_out = 0` | `P[j,ctrl] = rm` | `Q[j,j] = −1` | 0 |
| Spannungs-Steuertor | `i_ctrl = 0` (Leerlauf) | `P[j,j] = 1` | — | 0 |
| Strom-Steuertor | `u_ctrl = 0` (Kurzschluss) | — | `Q[j,j] = 1` | 0 |

### Zwei entscheidende Entwurfsentscheidungen

**1) Widerstand in Impedanzform, Kondensator in Admittanzform.**

- Schrieben wir den Widerstand als `u/R − i = 0`, entstünde bei symbolischem R der Bruch `1/R`.
- Schrieben wir den Kondensator als `u − i/(sC) = 0`, wäre die Matrix bei `s = 0` (DC)
  **singulär**.
- Mit unserer Wahl (`R·i − u = 0` und `sC·u − i = 0`) enthält die Matrix **überhaupt keine
  Brüche**. Das symbolische Ergebnis wird dadurch deutlich sauberer, und die DC-Analyse
  funktioniert problemlos.

**2) Vorzeichenkonvention: Bauelementparameter (+), Einheitskoeffizient (−).**

Die gesamte Zeile mit −1 zu multiplizieren wäre mathematisch äquivalent (die rechte Seite ist
null). Wir haben jedoch die Schreibweise von Insydes übernommen, damit die Matrizen direkt
vergleichbar bleiben.

---
---

# TEIL 2 — ALGORITHMUS (Kurzfassung)

Der Code führt genau diese acht Schritte in dieser Reihenfolge aus:

| # | Schritt | Verwendete Technik |
|---|---|---|
| 1 | Knoten indizieren, Masse auf 0 setzen | Wörterbuch + eigener Sortierschlüssel |
| 2 | Elemente in Zweige umwandeln | gesteuerte Quelle → 2 Zweige |
| 3 | Spannbaum bestimmen | **Union-Find** (mit Pfadverkürzung) |
| 4 | Knotenpotentiale durch Baumzweige ausdrücken | **BFS**, ausgehend von der Masse |
| 5 | Blöcke A und B füllen | zweigweises „Stempeln" |
| 6 | Blöcke P, Q, s füllen | `match/case` nach Elementtyp |
| 7 | Blöcke zur 2b×2b-Matrix zusammensetzen | `row_join` / `col_join` |
| 8 | Lösen | symbolisch: `LUsolve` · numerisch: `lambdify` + SciPy |

**Warum Union-Find?** Es ist der schnellste Weg, einen Baum aufzubauen (nahezu O(b)), und es
prüft nebenbei kostenlos, ob der Graph zusammenhängend ist. Verbindet ein Zweig zwei bisher
getrennte Teile, ist er ein **Baumzweig**; verbindet er zwei bereits verbundene Knoten, so
schließt er eine Masche und ist ein **Verbindungszweig**.

**Warum BFS?** Da im Baum der Weg zu jedem Knoten eindeutig ist, liefert eine einzige
Ausbreitung von der Masse aus sämtliche Potentialkoeffizienten eindeutig.

---
---

# TEIL 3 — TABELLE DER FUNKTIONSBLÖCKE

| # | Block | Funktionen | Erzeugte Mathematik |
|---|---|---|---|
| A | **Aufbau** | `Branch`, `__init__`, `generateValueDict` | Datenstruktur, `n`, `b`, `l` |
| B | **Topologie-Vorbereitung** | `_build_node_map`, `_build_branches` | Knotenindizes, Zweigliste |
| C | **Graph** | `_build_spanning_tree`, `_build_tree_potentials` | Baum, `twigs`/`links`, Koeffizienten `e_k` |
| D | **Unbekannte** | `_build_unknowns` | `x = [u \| i]` |
| E | **Topologieblöcke** | `buildIncidenceMatrix`, `buildLoopMatrix` | **A**, **B** |
| F | **Element-Stempel** | `add_impedance`, `add_admittance`, `add_independent_*`, `add_vcvs/vccs/cccs/ccvs`, `add_*_control_port` | Einträge in **P**, **Q**, **s** |
| G | **Elementblock** | `buildElementMatrices` | **P**, **Q**, **s** vollständig |
| H | **Zusammensetzung** | `buildRHS`, `buildTableau`, `buildEquationsSystem` | **T**, **RHS** |
| I | **Zugriffsmethoden** | `get_blocks`, `get_unknowns`, `get_tree_branches`, … | Schnittstelle für GUI/Präsentation |
| J | **Nachbearbeitung** | `_node_potential_expression`, `_is_node_request` | Rückgewinnung von `V_k` |
| K | **Löser** | `solve`, `solveAll`, `solveNumerical` | `x = T⁻¹·b` |

---
---

# TEIL 4 — FUNKTIONEN: AUFGABE + MATHEMATIK + CODE

## 4.0 Dateikopf, Importe und Konstanten

**Aufgabe:** lädt die verwendeten Bibliotheken und definiert zwei Konstanten.

- `GROUND_NAMES` — alle akzeptierten Schreibweisen der Masse. Die Masse erhält stets den
  Index **0** und wird aus der Matrix A gestrichen (§1.4).
- `CONTROLLED_SOURCES` — `E`, `G`, `F`, `H`. Diese vier Typen besitzen ein **zweites Tor**,
  sind also ein Element, erzeugen aber **zwei Zweige**. Das erklärt, warum `b` größer sein
  kann als die Zahl der Elemente.

`sympy` ist unser Computeralgebrasystem, `scipy` unser numerischer Löser.

```python
"""Normal sparse tableau analysis (STA) in the form used in the lecture.

The unknown vector holds branch quantities only, no node potentials. The
order of both the unknowns and the row blocks follows Analog Insydes'
SparseTableau.m (voltages before currents, KVL before KCL) so that this
tableau lines up column-for-column and row-for-row with Insydes' output:

    x = [ u_1 .. u_b | i_1 .. i_b ]^T          ->  2b unknowns

The tableau is built from the blocks A, B, P and Q:

    | B   0 |   | u |   | 0 |     <- (b-n+1) rows : KVL            B*u = 0
    | 0   A | * | i | = | 0 |     <- (n-1) rows   : KCL            A*i = 0
    | Q   P |           | s |     <-  b rows      : element eqs.   P*i + Q*u = s

Blocks
------
A : reduced incidence matrix, (n-1) x b.
    A[k,j] = +1 if branch j leaves node k, -1 if it enters, 0 otherwise.
    The ground row is dropped, which is the matrix form of choosing a
    reference node.

B : fundamental loop matrix, (b-n+1) x b.
    A spanning tree is chosen. Every branch outside the tree (a link) closes
    exactly one independent loop. B[k,j] is +1 / -1 / 0 depending on whether
    branch j runs with, against, or outside loop k. A * B^T = 0 always holds.

P, Q : current and voltage coefficients of the element equations, b x b.
    The rows are written the way Analog Insydes writes them: the element
    parameter (R, s*L, s*C, gain) carries the plus sign and the unit
    coefficient the minus sign, e.g. R*i - u = 0 for a resistor and
    s*C*u - i = 0 for a capacitor. Independent sources keep a positive unit
    coefficient so their entry in s keeps its sign.

s    : independent source vector, b x 1.

Relation to Modified_Node_Analysis
----------------------------------
This class deliberately follows the structure of ModifiedNodalAnalysis: the
same attribute names, the same netlist conventions, the same solver strategy
and one stamping method per element type. The mathematics differs because MNA
eliminates branch quantities in favour of node potentials, while the sparse
tableau keeps them and expresses KVL through loops instead of potentials.

Node potentials can still be recovered after solving by summing tree branch
voltages along the path from ground. That is a post processing step and is not
part of the tableau.
"""

import logging
from collections import deque

import numpy as np
import scipy.linalg as sla
import sympy as sp

import netlist.Circuit as Circuit
import Pspice_util as pu
from Equation_Formulator import EquationFormulator

logger = logging.getLogger(__name__)

GROUND_NAMES = ("0", "gnd", "GND", "ground", "Ground", "GROUND")

# element types that carry a second, controlling port
CONTROLLED_SOURCES = ("E", "G", "F", "H")
```

---

## 4.1 Klasse `Branch` — Datenstruktur eines Zweiges

**Aufgabe:** ein einfacher Datensatz, der einen Zweig darstellt (wie ein `struct` in C).

**Warum eine eigene Klasse?** Weil **Zweig ≠ Element**. Eine gesteuerte Quelle ist ein
Element, belegt aber zwei Zweige: das Ausgangstor und das Steuertor. Was die Zeilen- und
Spaltenzahl der Matrix bestimmt, ist nicht die Zahl der Elemente, sondern die **Zahl der
Zweige**.

**Mathematische Entsprechung:** `node_p` und `node_n` legen die **Zählpfeile** für `u` und `i`
fest. Sämtliche Vorzeichenregeln (±1 in A, ±1 in B) beruhen auf dieser Richtung: der Strom
verlässt `node_p` und tritt in `node_n` ein, die Spannung ist `u = e_p − e_n`.

Der Zusatz `_ctrl` sorgt dafür, dass sich die Symbole `I_E1` (Ausgang) und `I_E1_ctrl`
(Steuertor) nicht vermischen.

```python
class Branch:
    """One branch of the tableau.

    A branch is not the same thing as an element: a controlled source occupies
    two branches, the output port and the controlling port.

    Attributes:
        element (Element): the netlist element this branch belongs to.
        node_p (str): name of the positive node.
        node_n (str): name of the negative node.
        is_control (bool): True for the controlling port of a controlled source.
        symbol (str): base name used to build the I_ and U_ symbols.

    """

    def __init__(self, element, node_p, node_n, is_control=False):
        """Initialize the branch.

        Args:
            element (Element): the netlist element this branch belongs to.
            node_p (str): name of the positive node.
            node_n (str): name of the negative node.
            is_control (bool): True for the controlling port.

        """
        self.element = element
        self.node_p = node_p
        self.node_n = node_n
        self.is_control = is_control
        self.symbol = f"{element.get_symbol()}_ctrl" if is_control else element.get_symbol()
```

---

## 4.2 `__init__` — die Aufbaukette

**Aufgabe:** baut aus der Netzliste die gesamte Topologie auf und legt die Matrizen **leer** an
(gefüllt werden sie noch nicht).

**Mathematische Entsprechung — hier werden die Zahlen aus §1.2 berechnet:**

| Code | Mathematik |
|---|---|
| `self.n = len(self.node_map) - 1` | **n − 1** (Knoten ohne Masse) → Zeilenzahl von A |
| `self.m = len(self.branches)` | **b** (Zweigzahl) → Spaltenzahl aller Blöcke |
| `self.l = self.m - self.n` | **l = b − (n−1)** (unabhängige Maschen) → Zeilenzahl von B |

Auch die Matrixdimensionen werden hier festgelegt: `A` → (n−1)×b, `B` → l×b, `P`,`Q` → b×b,
`s_vec` → b×1, `RHS` → 2b×1.

**Warum `SparseMatrix`?** Eine dünnbesetzte Matrix speichert nur die Einträge ungleich null.
In unserer Matrix gibt es davon etwa `3b` Stück; eine dichte Matrix bräuchte `4b²` Zellen.
Daher der Name: **sparse** tableau.

```python
def __init__(self, circuit: Circuit):
    """Initialize the class.

    Args:
        circuit (Circuit): The Circuit to analyze. It has to be flattened,
            so it must not contain subcircuits or transistor models.

    """
    self.ct = circuit
    self.value_dict = self.generateValueDict(self.ct)
    self.s = sp.symbols("s")

    self._build_node_map()
    self._build_branches()

    # number of nodes without ground, written (n-1) in the lecture notes
    self.n = len(self.node_map) - 1
    # number of branches, written b in the lecture notes
    self.m = len(self.branches)

    self._build_spanning_tree()

    # number of independent loops, b - (n-1)
    self.l = self.m - self.n

    self.A = sp.SparseMatrix(self.n, self.m, {})
    self.B = sp.SparseMatrix(self.l, self.m, {})
    self.P = sp.SparseMatrix(self.m, self.m, {})
    self.Q = sp.SparseMatrix(self.m, self.m, {})
    self.s_vec = sp.SparseMatrix(self.m, 1, {})
    self.RHS = sp.SparseMatrix(2 * self.m, 1, {})
    self.T = sp.SparseMatrix(0, 0, {})

    self._build_unknowns()

    self.sym_result = {}
    self.num_result = {}
```

---

## 4.3 `generateValueDict` — Wörterbuch Symbol → Zahlenwert

**Aufgabe:** ordnet jedem Elementsymbol seinen Zahlenwert zu. Dieses Wörterbuch wird
**ausschließlich für die numerische Lösung** gebraucht; die symbolische Lösung rechnet mit
Symbolen.

**Detail — aus welchem Feld wird der Wert gelesen?** Das hängt vom Elementtyp ab:

| Typ | Feld | Begründung |
|---|---|---|
| R, L, C | `value_dc` | der Wert eines passiven Bauelements ist frequenzunabhängig |
| V, I | `value_ac` | in der Kleinsignalanalyse regt nicht der DC-Offset, sondern die **AC-Amplitude** an |
| E, F, G, H | `value` | der Verstärkungsfaktor der gesteuerten Quelle |

Fehlt der Wert, bleibt das Symbol **symbolisch** — das ist kein Fehler, sondern der Normalfall
der symbolischen Analyse. `pspice_to_float` wandelt PSPICE-Schreibweisen wie „1k" in `1000.0`;
schlägt das fehl (etwa bei einem Ausdruck wie `"2*R1"`), wird der Text mit `sympify`
symbolisch geparst.

```python
def generateValueDict(self, ct: Circuit):
    """Map every element symbol to its numerical value.

    The parameter that carries the value depends on the element type, in
    the same way as in ModifiedNodalAnalysis: passive elements use
    "value_dc", independent sources use "value_ac" for the small signal
    analysis and controlled sources use "value".

    Args:
        ct (Circuit): the circuit whose elements are read.

    Returns:
        dict: mapping from sympy symbol to float or symbolic expression.

    """
    value_dict = {}

    for element in ct.elements:
        symbol = sp.symbols(element.get_symbol())
        element_type = element.type.upper()

        match element_type:
            case "R" | "L" | "C":
                raw = element.params.get("value_dc")
            case "V" | "I":
                raw = element.params.get("value_ac", "0")
            case "E" | "F" | "G" | "H":
                raw = element.params.get("value")
            case _:
                continue

        if raw is None:
            logger.warning("Element %s has no value, its symbol stays symbolic.",
                           element.get_symbol())
            continue

        try:
            value_dict[symbol] = pu.pspice_to_float(str(raw))
        except (ValueError, TypeError):
            value_dict[symbol] = sp.sympify(raw)

    return value_dict
```

---

## 4.4 `_build_node_map` — Knotenname → Zeilenindex

**Aufgabe:** vergibt jedem Knoten einen Index. **Dieser Index ist die Zeilennummer des Knotens
in der Matrix A.**

**Mathematische Entsprechung:**
- Masse → Index **0** → **keine** Zeile in A (Wahl des Bezugsknotens, §1.4)
- übrige Knoten → 1, 2, 3, … → Zeilen 0, 1, 2, … in A (im Code `index - 1`)

**Warum ist die Sortierung wichtig?** Die Indexreihenfolge ist die Zeilenreihenfolge des
KCL-Blocks. Nummerierte man die Knoten nach ihrem ersten Auftreten in der Netzliste, wäre das
System weiterhin **korrekt**, die Zeilen wären gegenüber Insydes aber permutiert und die
Ausgaben nicht mehr direkt vergleichbar. Deshalb: **zuerst numerische Knoten (1, 2, …, 10) in
numerischer Reihenfolge, danach benannte Netze (`ua`, `out`) alphabetisch.**

Genau das leistet `_node_sort_key`: gelingt `int(name)`, gehört der Knoten in Gruppe 0
(numerisch), sonst in Gruppe 1 (alphabetisch).

**Fehlerprüfung:** fehlt die Masse → `ValueError`. Ohne Bezugsknoten sind die Potentiale nur
bis auf eine Konstante bestimmt — das System wäre singulär.

```python
def _build_node_map(self):
    """Map node names to consecutive indices, ground always to 0.

    The index of a node is the position of its KCL equation in the
    tableau, so the order has to be the one Analog Insydes uses:
    numbered nodes first and ascending, named nets after them,
    alphabetically. Numbering the nodes in order of first appearance in
    the netlist instead permutes the whole KCL block against Insydes'
    matrix - still a correct system, but no longer comparable row by row.
    SparseTableau (extended) already sorted them this way.

    Raises:
        ValueError: if the circuit has no ground node.

    """
    self.node_map = {}
    self._has_ground = False
    self._ground_name = None

    for node in self.ct.nodes:
        if node in GROUND_NAMES:
            self.node_map[node] = 0
            self._has_ground = True
            if self._ground_name is None:
                self._ground_name = node

    def _node_sort_key(name):
        # numeric node names sort as numbers (1, 2, ..., 10), everything
        # else (named nets like "ua") sorts alphabetically after them
        try:
            return (0, int(name), "")
        except ValueError:
            return (1, 0, name)

    non_ground_nodes = sorted(
        {node for node in self.ct.nodes if node not in self.node_map},
        key=_node_sort_key,
    )
    for index, node in enumerate(non_ground_nodes, start=1):
        self.node_map[node] = index

    if not self._has_ground:
        raise ValueError(
            "No ground node found. The normal sparse tableau needs a "
            "reference node (name it '0' or 'GND')."
        )
```

---

## 4.5 `_build_branches` — Elementliste → Zweigliste

**Aufgabe:** wandelt die Netzlistenelemente in Zweige um. **Die Reihenfolge dieser Liste legt
die Spaltenreihenfolge der gesamten Matrix und die Zeilenreihenfolge der
Bauelementgleichungen fest.**

**Das wichtigste Detail:** eine gesteuerte Quelle legt ihr Steuertor **unmittelbar nach** dem
Ausgangstor auf den Index `j+1`. Nur dadurch können wir in den Stempeln

```
self.add_vcvs(j, j + 1, symbol)
```

schreiben — dass `j+1` das Steuertor ist, ist **garantiert**. Das ist die eleganteste, zugleich
aber empfindlichste Annahme des Codes: gerät die Reihenfolge durcheinander, schreiben alle
Stempel gesteuerter Quellen in die falsche Spalte.

**Mathematische Entsprechung:** `b = len(self.branches)`. In einem Netzwerk mit drei
Elementen, von denen eines eine gesteuerte Quelle ist, gilt also `b = 4` und damit `2b = 8`
Unbekannte.

```python
def _build_branches(self):
    """Turn the element list into the branch list.

    The order of this list fixes the row and column order of the tableau.
    A controlled source appends its controlling port directly after its
    output port, which is what the j+1 indexing in the stamps relies on.

    Raises:
        ValueError: if an element has too few connections or refers to an
            unknown node.

    """
    self.branches = []

    for element in self.ct.elements:
        connections = element.connections

        if len(connections) < 2:
            raise ValueError(
                f"Element {element.get_symbol()} has less than two connections."
            )

        for node in connections:
            if node not in self.node_map:
                raise ValueError(
                    f"Node {node} of element {element.get_symbol()} is unknown. "
                    "Call circuit.update_nodes() first."
                )

        self.branches.append(Branch(element, connections[0], connections[1]))

        if element.type.upper() in CONTROLLED_SOURCES:
            if len(connections) < 4:
                raise ValueError(
                    f"Controlled source {element.get_symbol()} needs four connections."
                )
            self.branches.append(
                Branch(element, connections[2], connections[3], is_control=True)
            )
```

---

## 4.6 `_build_spanning_tree` — Spannbaum (Union-Find)

**Aufgabe:** teilt die Zweige in zwei Gruppen: **Baumzweige** (`twigs`) und
**Verbindungszweige** (`links`).

**Mathematische Entsprechung — die Umsetzung von §1.2:**
- `len(self.twigs) == n − 1` (immer)
- `len(self.links) == l = b − n + 1` → **Zeilenzahl der Matrix B**

**Wie arbeitet Union-Find?**
Anfangs ist jeder Knoten seine eigene Menge. Jeder Zweig wird der Reihe nach angeboten:
- liefert `union(p, n)` **True** → zwei getrennte Teile wurden verbunden → **Baumzweig**
- liefert `union(p, n)` **False** → beide waren bereits verbunden → der Zweig schließt eine
  **Masche** → **Verbindungszweig**

Die Zeile `parent[x] = parent[parent[x]]` in `find` ist die **Pfadverkürzung**: sie flacht die
Kette ab und beschleunigt spätere Suchen.

**Kostenlose Zusatzprüfung:** ist die Zahl der Baumzweige nicht `n−1`, so ist der Graph
**nicht zusammenhängend** — es gibt eine von der Masse aus unerreichbare Insel. Der Code
meldet das mit `ValueError`.

**Warum kein „normaler Baum"?** In Lehrbüchern wird empfohlen, Spannungsquellen in den Baum
und Stromquellen in den Kobaum zu legen. Wir verwenden die **Netzlistenreihenfolge**, weil
Insydes es ebenso macht. Ein anderer Baum → eine andere, aber **äquivalente** Matrix B;
`A·Bᵀ = 0` und die Lösung bleiben unverändert, lediglich die ausgegebenen KVL-Zeilen sehen
anders aus.

```python
def _build_spanning_tree(self):
    """Split the branches into tree branches and links.

    Union-Find is used: a branch that joins two so far separate parts of
    the graph is a tree branch, otherwise it closes a loop and is a link.

    The branches are offered in plain branch order, which is the order of
    the netlist. That is what Analog Insydes' SparseTableau.m does, and it
    is what makes the KVL block line up with Insydes' row for row. Sorting
    them into a "normal tree" first (voltage sources into the tree,
    current sources into the co-tree, storage elements in between) yields
    a different but equally valid tree: A * B^T = 0 and the solution are
    unchanged, only the printed KVL rows differ. Insydes does not do it,
    so neither does this.

    Raises:
        ValueError: if the circuit graph is not connected.

    """
    parent = {node: node for node in self.node_map}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        parent[ra] = rb
        return True

    self.twigs = []
    self.links = []

    for j, branch in enumerate(self.branches):
        if union(branch.node_p, branch.node_n):
            self.twigs.append(j)
        else:
            self.links.append(j)

    self.twigs.sort()
    self.links.sort()

    expected = len(self.node_map) - 1
    if len(self.twigs) != expected:
        raise ValueError(
            f"The circuit graph is not connected: found {len(self.twigs)} tree "
            f"branches but expected {expected}. Every node must be reachable "
            "from ground."
        )

    self._build_tree_potentials()
```

---

## 4.7 `_build_tree_potentials` — Potentiale durch Baumzweige (BFS)

**Aufgabe:** setzt Schritt 1 aus §1.5 um. Jedes Knotenpotential wird als
vorzeichenbehaftete Summe von Baumzweigspannungen ausgedrückt:

$$ e_k \;=\; \sum_{j \in \text{Weg}} c_{kj}\, u_j
\qquad\Rightarrow\qquad \texttt{node\_potential\_coeffs[k] = \{j: c\}} $$

**Die Vorzeichenregel im Code:**

```
adjacency[node_p].append((node_n, j, -1))   # Gang p → n:  e_n = e_p − u_j
adjacency[node_n].append((node_p, j, +1))   # Gang n → p:  e_p = e_n + u_j
```

**Warum BFS und warum von der Masse aus?** Das Massepotential ist null → das Startwörterbuch
ist **leer** (`{}`), also `e_0 = 0`. Da der Baum kreisfrei ist, gibt es zu jedem Knoten genau
einen Weg; eine einzige Ausbreitung per BFS liefert daher alle Koeffizienten eindeutig. Die
Zeile `if neighbour in ...: continue` überspringt bereits besuchte Knoten.

**Dieses Wörterbuch wird an zwei Stellen gebraucht:**
1. `buildLoopMatrix` → zum Aufbau der Matrix B
2. `_node_potential_expression` → um nach dem Lösen Knotenspannungen wie `V_2`
   zurückzugewinnen

```python
def _build_tree_potentials(self):
    """Express every node potential through tree branch voltages.

    The tree is rooted at ground. For a tree branch j the relation
    u_j = e_p - e_n gives:

        walking from p to n:  e_n = e_p - u_j   ->  coefficient -1
        walking from n to p:  e_p = e_n + u_j   ->  coefficient +1

    The result is stored as node_potential_coeffs[node] = {branch: factor}
    and is used both for the loop matrix and for recovering node
    potentials after the solve.

    """
    adjacency = {node: [] for node in self.node_map}
    for j in self.twigs:
        branch = self.branches[j]
        adjacency[branch.node_p].append((branch.node_n, j, -1))
        adjacency[branch.node_n].append((branch.node_p, j, +1))

    self.node_potential_coeffs = {self._ground_name: {}}

    queue = deque([self._ground_name])
    while queue:
        current = queue.popleft()
        for neighbour, j, sign in adjacency[current]:
            if neighbour in self.node_potential_coeffs:
                continue
            coeffs = dict(self.node_potential_coeffs[current])
            coeffs[j] = coeffs.get(j, 0) + sign
            self.node_potential_coeffs[neighbour] = coeffs
            queue.append(neighbour)
```

---

## 4.8 `_build_unknowns` — Unbekanntenvektor `x`

**Aufgabe:** erzeugt die Symbole des Vektors `x`.

**Mathematische Entsprechung — das ist unmittelbar die Definition aus §1.1:**

$$ x = [\, u_1 \dots u_b \mid i_1 \dots i_b \,]^T, \qquad \dim x = 2b $$

**Die Reihenfolge ist entscheidend:** erst alle Spannungen, dann alle Ströme. Genau das ist
auch die Spaltenreihenfolge von T (deshalb stehen in `buildTableau` `Q.row_join(P)` und
`B.row_join(0)` in dieser Reihenfolge). Bei umgekehrter Reihenfolge müssten auch die Blöcke
von T vertauscht werden.

```python
def _build_unknowns(self):
    """Build the unknown vector [ u_1..u_b | i_1..i_b ], Insydes order."""
    current_symbols = [sp.Symbol(f"I_{branch.symbol}") for branch in self.branches]
    voltage_symbols = [sp.Symbol(f"U_{branch.symbol}") for branch in self.branches]

    self.unknowns = sp.Matrix(voltage_symbols + current_symbols)
```

---

## 4.9 `buildIncidenceMatrix` — **Block A**

**Aufgabe:** füllt die Matrix A aus §1.4. Dimension: **(n−1) × b**.

**Zuordnung Code ↔ Mathematik:**

| Codezeile | Mathematik |
|---|---|
| `for j, branch in enumerate(...)` | `j` = Spaltennummer = Zweigindex |
| `if index_p != 0: A[index_p-1, j] += 1` | der Strom **verlässt** `node_p` → `+1` |
| `if index_n != 0: A[index_n-1, j] -= 1` | der Strom **tritt ein** in `node_n` → `−1` |
| Bedingung `if index != 0` | **Massezeile wird ausgelassen** = Wahl des Bezugsknotens |
| `index - 1` | die Zeilen verschieben sich um eins, weil die Masse entfällt |

`+=` / `-=` werden verwendet, damit sich die Koeffizienten aufheben, falls beide Enden eines
Zweiges am selben Knoten liegen (entarteter Fall).

**Ergebnis:** jede Zeile von `A·i = 0` ist die KCL-Gleichung eines Knotens.

```python
def buildIncidenceMatrix(self):
    """Build block A, the reduced incidence matrix.

    Returns:
        A (matrix): incidence matrix of shape (n-1) x b.

    """
    self.A = sp.SparseMatrix(self.n, self.m, {})

    for j, branch in enumerate(self.branches):
        index_p = self.node_map[branch.node_p]
        index_n = self.node_map[branch.node_n]

        if index_p != 0:
            self.A[index_p - 1, j] += 1
        if index_n != 0:
            self.A[index_n - 1, j] -= 1

    return self.A
```

---

## 4.10 `buildLoopMatrix` — **Block B**

**Aufgabe:** füllt die Matrix B aus §1.5. Dimension: **l × b**.

**Zuordnung Code ↔ Mathematik — drei Zeilen, drei Terme:**

$$ \underbrace{u_{\text{link}}}_{\texttt{B[k,j] += 1}} \;\;\underbrace{-\;c_p\cdot u}_{\texttt{B[k,twig] -= coeff}} \;\;\underbrace{+\;c_n\cdot u}_{\texttt{B[k,twig] += coeff}} \;=\; 0 $$

| Codezeile | Mathematik |
|---|---|
| `for k, j in enumerate(self.links)` | `k` = Maschennummer (Zeile), `j` = Verbindungszweig |
| `self.B[k, j] += 1` | der Verbindungszweig geht mit `+1` in seine eigene Masche ein |
| `for twig, coeff in ...[node_p]: B[k,twig] -= coeff` | der Term `− e_p` |
| `for twig, coeff in ...[node_n]: B[k,twig] += coeff` | der Term `+ e_n` |

**Kerngedanke:** nirgendwo wird nach Maschen „gesucht". Da die Baumpotentiale bereits
vorliegen, liefert jeder Verbindungszweig **unmittelbar** eine Maschengleichung. Das ist der
Kniff, der die STA am Rechner überhaupt umsetzbar macht.

**Verifikation:** `A * B.T == 0` — die stärkste Einzeiler-Demonstration für die Präsentation.

```python
def buildLoopMatrix(self):
    """Build block B, the fundamental loop matrix.

    Every link closes exactly one loop. Walking that loop over the tree
    gives u_link = e_p - e_n = (c[p] - c[n]) . u, which rearranges into
    the loop equation u_link - (c[p] - c[n]) . u = 0.

    Returns:
        B (matrix): loop matrix of shape (b-n+1) x b.

    """
    self.B = sp.SparseMatrix(self.l, self.m, {})

    for k, j in enumerate(self.links):
        branch = self.branches[j]

        self.B[k, j] += 1

        for twig, coeff in self.node_potential_coeffs[branch.node_p].items():
            self.B[k, twig] -= coeff
        for twig, coeff in self.node_potential_coeffs[branch.node_n].items():
            self.B[k, twig] += coeff

    return self.B
```

---

## 4.11 Element-Stempel — passive Bauelemente

**Aufgabe:** schreibt für R, L und C die **Diagonaleinträge** von P und Q.

$$ \text{Impedanzform: } Z\cdot i - u = 0 \qquad\qquad \text{Admittanzform: } Y\cdot u - i = 0 $$

| Funktion | verwendet für | Gleichung | P | Q |
|---|---|---|---|---|
| `add_impedance` | R (Z=R), L (Z=sL) | `Z·i − u = 0` | `+Z` | `−1` |
| `add_admittance` | C (Y=sC) | `Y·u − i = 0` | `−1` | `+Y` |

**Warum werden beide Formen gemischt?** Wegen der zwei Entscheidungen aus §1.6:
- Widerstand in Impedanzform → **kein** Bruch `1/R`
- Kondensator in Admittanzform → **kein** `1/(sC)` → **keine** Singularität bei `s=0`

Ergebnis: **die Matrix enthält keinerlei Brüche.** Deshalb fallen die symbolischen Ergebnisse
so sauber aus.

```python
def add_impedance(self, row, impedance):
    """Add an element described by its impedance: Z * i - u = 0.

    Used for R (Z = R) and L (Z = s*L). Writing the resistor in impedance
    form avoids the 1/R division that nodal analysis needs.

    The row is written the way Analog Insydes writes it: the element
    parameter carries the plus sign and the unit coefficient carries the
    minus sign. Multiplying the row by -1 would give the equivalent
    u - Z * i = 0; the solution is the same either way, because the right
    hand side of this row is zero.

    Args:
        row (int): branch index, which is also the equation row.
        impedance (symbol): symbolic impedance of the branch.

    """
    self.P[row, row] = impedance
    self.Q[row, row] = -1

def add_admittance(self, row, admittance):
    """Add an element described by its admittance: Y * u - i = 0.

    Used for C (Y = s*C). The admittance form is chosen here so that no
    1/(s*C) term appears, which would be singular at s = 0.

    Sign convention as in add_impedance: parameter positive, unit
    coefficient negative, matching Analog Insydes.

    Args:
        row (int): branch index, which is also the equation row.
        admittance (symbol): symbolic admittance of the branch.

    """
    self.P[row, row] = -1
    self.Q[row, row] = admittance
```

---

## 4.12 Element-Stempel — unabhängige Quellen

**Aufgabe:** schreibt die Gleichung für V und I **und füllt den Vektor `s`**.

$$ u = V \quad\Rightarrow\quad Q[j,j]=1,\; s[j]=V
\qquad\qquad
i = I \quad\Rightarrow\quad P[j,j]=1,\; s[j]=I $$

**Das sind die einzigen „anregenden" Zeilen des Systems.** Bei allen anderen Zeilen ist die
rechte Seite null. In der Präsentation: *„hier und nur hier wird das Netzwerk getrieben"*.

**Warum ist der Einheitskoeffizient hier `+1`?** Bei den passiven Elementen war es `−1`. Hier
ist er `+1`, weil der Quellenwert auf die rechte Seite wandert; mit `−1` würde sich sein
Vorzeichen umkehren.

```python
def add_independent_voltage_source(self, row, sym_value):
    """Add an independent voltage source: u = V.

    The polarity follows the netlist, connections[0] is the plus terminal.

    Args:
        row (int): branch index of the source.
        sym_value (symbol): symbol of the source.

    """
    self.Q[row, row] = 1
    self.s_vec[row] = sym_value

def add_independent_current_source(self, row, sym_value):
    """Add an independent current source: i = I.

    The current flows from connections[0] to connections[1] through the
    element, the same direction convention as in ModifiedNodalAnalysis.

    Args:
        row (int): branch index of the source.
        sym_value (symbol): symbol of the source.

    """
    self.P[row, row] = 1
    self.s_vec[row] = sym_value
```

---

## 4.13 Element-Stempel — gesteuerte Quellen

**Aufgabe:** schreibt die **außerdiagonalen** Einträge der vier Typen gesteuerter Quellen.
Genau hier entsteht die Kopplung.

| Funktion | Typ | Gleichung | Einträge |
|---|---|---|---|
| `add_vcvs` | E | `μ·u_ctrl − u_out = 0` | `Q[j,j]=−1`, `Q[j,ctrl]=μ` |
| `add_vccs` | G | `gm·u_ctrl − i_out = 0` | `P[j,j]=−1`, `Q[j,ctrl]=gm` |
| `add_cccs` | F | `β·i_ctrl − i_out = 0` | `P[j,j]=−1`, `P[j,ctrl]=β` |
| `add_ccvs` | H | `rm·i_ctrl − u_out = 0` | `Q[j,j]=−1`, `P[j,ctrl]=rm` |

**Einfache Merkregel:**
- Ist der Ausgang eine **Spannung**, geht die `−1` nach **Q**; ist er ein **Strom**, nach **P**.
- Ist die Steuergröße eine **Spannung**, geht die Verstärkung nach **Q**; ist sie ein
  **Strom**, nach **P**.

G und H sind „gemischte" Zeilen: ein Eintrag liegt in P, der andere in Q. Diese Zeile berührt
also sowohl `u`- als auch `i`-Unbekannte — das ist die Kopplung.

Die Spalte `ctrl` ist stets `j+1` (§4.5).

```python
def add_vcvs(self, row, ctrl_row, gain):
    """Add a voltage controlled voltage source: gain * u_ctrl - u_out = 0.

    Sign convention as in add_impedance: the gain carries the plus sign,
    the unit coefficient the minus sign, matching Analog Insydes.

    Args:
        row (int): branch index of the output port.
        ctrl_row (int): branch index of the controlling port.
        gain (symbol): gain factor.

    """
    self.Q[row, row] = -1
    self.Q[row, ctrl_row] = gain

def add_vccs(self, row, ctrl_row, gm):
    """Add a voltage controlled current source: gm * u_ctrl - i_out = 0.

    Args:
        row (int): branch index of the output port.
        ctrl_row (int): branch index of the controlling port.
        gm (symbol): transconductance.

    """
    self.P[row, row] = -1
    self.Q[row, ctrl_row] = gm

def add_cccs(self, row, ctrl_row, beta):
    """Add a current controlled current source: beta * i_ctrl - i_out = 0.

    Args:
        row (int): branch index of the output port.
        ctrl_row (int): branch index of the controlling port.
        beta (symbol): current gain.

    """
    self.P[row, row] = -1
    self.P[row, ctrl_row] = beta

def add_ccvs(self, row, ctrl_row, r_m):
    """Add a current controlled voltage source: r_m * i_ctrl - u_out = 0.

    Args:
        row (int): branch index of the output port.
        ctrl_row (int): branch index of the controlling port.
        r_m (symbol): transresistance.

    """
    self.Q[row, row] = -1
    self.P[row, ctrl_row] = r_m
```

---

## 4.14 Element-Stempel — Steuertore

**Aufgabe:** schreibt eine Gleichung für den **zweiten Zweig** einer gesteuerten Quelle. Auch
dieser Zweig muss eine Gleichung liefern, sonst wäre die 2b×2b-Struktur nicht mehr quadratisch.

**Die Physik dahinter:**

| Tor | misst | ideales Verhalten | Gleichung | Stempel |
|---|---|---|---|---|
| Spannungssteuerung (E, G) | Spannung | ideales **Voltmeter**, zieht keinen Strom | `i_ctrl = 0` (Leerlauf) | `P[j,j] = 1` |
| Stromsteuerung (F, H) | Strom | ideales **Amperemeter**, kein Spannungsabfall | `u_ctrl = 0` (Kurzschluss) | `Q[j,j] = 1` |

**Ein schöner Satz für die Präsentation:** *„Ein Messgerät darf das Netzwerk nicht
beeinflussen — der Innenwiderstand eines Voltmeters ist unendlich, der eines Amperemeters
null. Genau das haben wir als Gleichung hingeschrieben."*

```python
def add_voltage_control_port(self, row):
    """Add the controlling port of a VCVS or VCCS: i_ctrl = 0.

    A port that senses a voltage must behave like a voltmeter and draw no
    current, so the port is an open circuit.

    Args:
        row (int): branch index of the controlling port.

    """
    self.P[row, row] = 1

def add_current_control_port(self, row):
    """Add the controlling port of a CCCS or CCVS: u_ctrl = 0.

    A port that senses a current must behave like an ammeter and drop no
    voltage, so the port is a short circuit.

    Args:
        row (int): branch index of the controlling port.

    """
    self.Q[row, row] = 1
```

---

## 4.15 `buildElementMatrices` — **die Blöcke P, Q, s vollständig**

**Aufgabe:** läuft über alle Zweige und ruft für jeden den passenden Stempel auf.

$$ P[j,:]\cdot i \;+\; Q[j,:]\cdot u \;=\; s[j], \qquad j = 0 \dots b-1 $$

**Ablauflogik:**
1. Ist der Zweig ein **Steuertor**? → das Flag `is_control` prüfen → bei E/G Leerlauf, bei F/H
   Kurzschluss → `continue` (keine Bauelementgleichung)
2. Andernfalls `match/case` nach Typ → genau ein Stempelaufruf

**Detail 1 — `s * symbol`:** bei der Spule `sL`, beim Kondensator `sC`. Hier tritt die
Laplace-Variable in die Gleichungen ein. Die Frequenzabhängigkeit entsteht **ausschließlich**
aus diesen beiden Zeilen.

**Detail 2 — `if "value_ac" in element.params`:** eine Quelle ohne AC-Wert regt in der
Kleinsignalanalyse nicht an, es wird `0` eingetragen. Das entspricht dem Verhalten von
DC-Versorgungsquellen, die in der AC-Analyse wie ein Kurzschluss wirken.

**Detail 3 — `j + 1`:** der Index des Steuertores (die Garantie aus §4.5).

**Fehlerprüfung:** ein nicht unterstützter Typ (z. B. ein Transistormodell) → `ValueError`.
Die Schaltung muss zuvor aufgelöst (geflattet) worden sein.

```python
def buildElementMatrices(self):
    """Build blocks P and Q and the source vector s.

    Row j holds the element equation of branch j:

        P[j, :] . i  +  Q[j, :] . u  =  s[j]

    Returns:
        P (matrix): current coefficients, b x b.
        Q (matrix): voltage coefficients, b x b.

    Raises:
        ValueError: if an element type is not supported, which usually
            means the circuit has not been flattened.

    """
    s = self.s

    self.P = sp.SparseMatrix(self.m, self.m, {})
    self.Q = sp.SparseMatrix(self.m, self.m, {})
    self.s_vec = sp.SparseMatrix(self.m, 1, {})

    for j, branch in enumerate(self.branches):
        element = branch.element
        symbol = sp.symbols(element.get_symbol())
        element_type = element.type.upper()

        if branch.is_control:
            if element_type in ("E", "G"):
                self.add_voltage_control_port(j)
            else:
                self.add_current_control_port(j)
            continue

        match element_type:
            case "R":
                self.add_impedance(j, symbol)
            case "L":
                self.add_impedance(j, s * symbol)
            case "C":
                self.add_admittance(j, s * symbol)
            case "V":
                excitation = symbol if "value_ac" in element.params else sp.Integer(0)
                self.add_independent_voltage_source(j, excitation)
            case "I":
                excitation = symbol if "value_ac" in element.params else sp.Integer(0)
                self.add_independent_current_source(j, excitation)
            case "E":
                self.add_vcvs(j, j + 1, symbol)
            case "G":
                self.add_vccs(j, j + 1, symbol)
            case "F":
                self.add_cccs(j, j + 1, symbol)
            case "H":
                self.add_ccvs(j, j + 1, symbol)
            case _:
                raise ValueError(
                    f"Element type '{element.type}' of {element.get_symbol()} is not "
                    "supported. Flatten the circuit before running the analysis."
                )

    return self.P, self.Q
```

---

## 4.16 `buildRHS` — Vektor der rechten Seite

**Aufgabe:** baut die rechte Seite der Größe `2b × 1`.

$$ \text{RHS} = \begin{bmatrix} 0_{\;l} \\ 0_{\;n-1} \\ s_{\;b} \end{bmatrix} $$

**Warum ist der obere Teil null?** Weil die Kirchhoffschen Gesetze homogen sind (§1.3).
Angeregt wird nur durch unabhängige Quellen, und die stehen in `s_vec`.

`col_join` = vertikales Anfügen (Zeilen untereinander). Das Gegenstück `row_join` = horizontal.

```python
def buildRHS(self):
    """Build the right hand side: zeros for KCL and KVL, then s.

    Returns:
        RHS (vector): right hand side of length 2b.

    """
    top_zeros = sp.SparseMatrix(self.n + self.l, 1, {})
    self.RHS = top_zeros.col_join(self.s_vec)
    return self.RHS
```

---

## 4.17 `buildTableau` — **Zusammensetzung der Matrix T**

**Aufgabe:** fügt die vier Blöcke in die 2b×2b-Matrix aus §1.3 ein.

| Code | Blockzeile | Bedeutung |
|---|---|---|
| `top = B.row_join(0)` | `[ B \| 0 ]` | KVL schränkt nur die **Spannungen** ein |
| `middle = 0.row_join(A)` | `[ 0 \| A ]` | KCL schränkt nur die **Ströme** ein |
| `bottom = Q.row_join(P)` | `[ Q \| P ]` | die Bauelementgleichungen verknüpfen **beide** |
| `top.col_join(middle).col_join(bottom)` | vertikales Stapeln | `l + (n−1) + b = 2b` Zeilen |

**In der Präsentation betonen:** die Nullblöcke sind kein Zufall, sondern eine physikalische
Aussage. Die Kirchhoffschen Gesetze kennen die Bauelementwerte **überhaupt nicht** — sie
kennen nur die Topologie. Die gesamte Bauelementinformation steckt im unteren Block.

```python
def buildTableau(self):
    """Assemble the blocks into the system matrix T.

    Column order is [u | i] and row order is [KVL | KCL | element eqs.],
    matching Analog Insydes' SparseTableau.m.

    Returns:
        T (matrix): system matrix of shape 2b x 2b.

    """
    top = self.B.row_join(sp.SparseMatrix(self.l, self.m, {}))
    middle = sp.SparseMatrix(self.n, self.m, {}).row_join(self.A)
    bottom = self.Q.row_join(self.P)

    self.T = top.col_join(middle).col_join(bottom)
    return self.T
```

---

## 4.18 `buildEquationsSystem` — die zentrale Aufbaufunktion

**Aufgabe:** ruft die fünf Schritte in der richtigen Reihenfolge auf. Der „Dirigent", der sich
in der Präsentation auf einer einzigen Folie zeigen lässt.

```
buildIncidenceMatrix()   →  A
buildLoopMatrix()        →  B
buildElementMatrices()   →  P, Q, s
buildRHS()               →  RHS
buildTableau()           →  T
```

Die Reihenfolge ist wesentlich: `buildTableau` setzt voraus, dass A, B, P und Q gefüllt sind;
`buildRHS` setzt voraus, dass `s_vec` gefüllt ist, muss also nach `buildElementMatrices`
kommen.

```python
def buildEquationsSystem(self):
    """Build the equation system based on the circuit description.

    Returns:
        T (matrix): system matrix.
        RHS (vector): right hand side.

    """
    self.buildIncidenceMatrix()
    self.buildLoopMatrix()
    self.buildElementMatrices()
    self.buildRHS()
    self.buildTableau()

    logger.debug("Finished building equation system!")
    return self.T, self.RHS
```

---

## 4.19 Zugriffsmethoden

**Aufgabe:** öffnen das aufgebaute System nach außen (GUI, Tests, Präsentation). Sie erzeugen
keine Mathematik, sind aber **für die Präsentation sehr wertvoll**:

| Funktion | zeigt |
|---|---|
| `get_blocks()` | A, B, P, Q, s **einzeln** → direkter Vergleich mit den Vorlesungsunterlagen |
| `get_equation_system()` | T und RHS |
| `get_unknowns()` | den Vektor `x` |
| `get_tree_branches()` / `get_link_branches()` | **welchen Baum** das Programm gewählt hat |
| `get_solvable_names()` | alles Lösbare: Zweiggrößen + Knotenpotentiale `V_k` |

`get_solvable_names()` ist bemerkenswert: Knotenpotentiale sind im Tableau **keine
Unbekannten**, werden aber in die Liste aufgenommen, weil sie sich aus dem Baum zurückgewinnen
lassen (§4.21).

```python
def get_equation_system(self):
    """Return the equation system.

    Returns:
        T (matrix): system matrix of the equation system.
        RHS (vector): right hand side of the equation system.

    """
    return self.T, self.RHS

def get_blocks(self):
    """Return the blocks A, B, P, Q and s separately.

    Returns:
        tuple: (A, B, P, Q, s) as used in the lecture notes.

    """
    return self.A, self.B, self.P, self.Q, self.s_vec

def get_unknowns(self):
    """Return the vector of unknown branch currents and branch voltages.

    Returns:
        x (vector): vector of unknowns, length 2b.

    """
    return self.unknowns

def get_unknowns_as_strings(self):
    """Return the vector of unknowns as strings for easy displaying.

    Returns:
        String (array): vector of unknowns as string.

    """
    return [str(symbol) for symbol in self.get_unknowns()]

def get_solvable_names(self):
    """Return every name that solve() accepts.

    On top of the real unknowns this adds the node potentials, which are
    not part of the tableau but can be recovered from it. The GUI uses
    this list to fill its output selection.

    Returns:
        String (array): unknowns followed by node potential names.

    """
    node_names = [
        f"V_{name}" for name, index in self.node_map.items() if index != 0
    ]
    return self.get_unknowns_as_strings() + node_names

def get_tree_branches(self):
    """Return the symbol names of the tree branches.

    Returns:
        String (array): names of the branches inside the spanning tree.

    """
    return [self.branches[j].symbol for j in self.twigs]

def get_link_branches(self):
    """Return the symbol names of the link branches.

    Returns:
        String (array): names of the branches outside the spanning tree.

    """
    return [self.branches[j].symbol for j in self.links]

def get_System_Inputs(self):
    """Get the input variables of the system.

    Returns:
        inputs (array): array with input variables.

    """
    return [str(entry) for entry in self.RHS]
```

---

## 4.20 Hilfsfunktionen (Eingang ändern, Index bestimmen)

**Aufgabe:** kleine Arbeiten vor dem Lösen.

- `modify_Input` — ersetzt die rechte Seite (z. B. um eine andere Anregung zu testen). Arbeitet
  auf einer **Kopie**, das Original bleibt unangetastet.
- `_index_of` — findet die Position einer Unbekannten in `x`. Sagt also, in welcher Zeile des
  Lösungsvektors z. B. `I_R1` steht.
- `_resolve_rhs` — nimmt bei passender Länge die geänderte rechte Seite, sonst wird gewarnt
  und das Original verwendet.

```python
def modify_Input(self, new_value: list):
    """Replace the right hand side entries by the given values.

    Args:
        new_value (list): one entry per row of the right hand side.

    Returns:
        RHS (vector): a modified copy, the original stays untouched.

    """
    rhs_modified = self.RHS.copy()
    for index, value in enumerate(new_value):
        rhs_modified[index] = sp.sympify(value)
    return rhs_modified

def _index_of(self, unknown_variable: str):
    """Return the position of an unknown inside the solution vector.

    Args:
        unknown_variable (str): name of the unknown.

    Returns:
        int: index inside the solution vector.

    Raises:
        ValueError: if the name is not an unknown of the system.

    """
    symbol = sp.symbols(unknown_variable)
    unknown_list = list(self.get_unknowns())
    if symbol not in unknown_list:
        raise ValueError(f"Unknown variable '{unknown_variable}' is not in the system.")
    return unknown_list.index(symbol)

def _resolve_rhs(self, input_modification):
    """Pick the right hand side to solve with.

    Args:
        input_modification (list): replacement values, may be empty.

    Returns:
        RHS (vector): modified copy if the length matches, else the original.

    """
    if len(input_modification) == len(self.RHS):
        return self.modify_Input(input_modification)
    if input_modification:
        logger.warning("Input modification has the wrong length, using the original RHS.")
    return self.RHS
```

---

## 4.21 Rückgewinnung der Knotenpotentiale

**Aufgabe:** berechnet **nach** dem Lösen Knotenspannungen wie `V_2`.

**Warum ist das nötig?** Unter den Unbekannten der normalen STA gibt es **keine**
Knotenpotentiale (§1.1). Der Anwender möchte die Übertragungsfunktion aber meist in der Form
`V_out / V_in`.

**Die Mathematik — Schritt 1 aus §1.5, rückwärts gelesen:**

$$ e_k \;=\; \sum_{j \in \text{Baumweg}} c_{kj}\cdot x[j] $$

Die Koeffizienten wurden in `_build_tree_potentials` **bereits berechnet**; hier werden sie nur
noch mit dem Lösungsvektor multipliziert und aufsummiert. Es wird also keine zusätzliche
Gleichung gelöst — reine **Nachbearbeitung**.

`_is_node_request` ist lediglich ein Parser: beginnt der Name mit `V_` und ist der Rest ein
gültiger Knotenname, dann handelt es sich um eine Knotenanfrage.

```python
def _node_potential_expression(self, node_name: str, solution):
    """Sum the tree branch voltages on the path from ground to a node.

    Args:
        node_name (str): name of the node.
        solution (vector): solved unknown vector.

    Returns:
        sympy.Expr: the node potential.

    Raises:
        ValueError: if the node is not part of the circuit.

    """
    if node_name not in self.node_potential_coeffs:
        raise ValueError(f"Node '{node_name}' is not part of the circuit.")

    expression = sp.Integer(0)
    for twig, coeff in self.node_potential_coeffs[node_name].items():
        expression += coeff * solution[twig]
    return expression

def _is_node_request(self, name: str):
    """Check whether a name asks for a node potential.

    Args:
        name (str): requested name, for example "V_2".

    Returns:
        str | None: the node name, or None if this is not a node request.

    """
    if not name.startswith("V_"):
        return None
    node_name = name[2:]
    return node_name if node_name in self.node_map else None
```

---

## 4.22 `solve` — symbolische Lösung (eine Größe)

**Aufgabe:** löst `T·x = RHS` symbolisch und liefert die eine gewünschte Größe zurück.

**Die Mathematik:**

$$ x = T^{-1}\,b \quad\text{(praktisch über die LU-Zerlegung)} $$

**Warum `LUsolve` und nicht `sp.solve`?** `sp.solve` ist ein Allzweck-Gleichungslöser und bei
symbolischen Matrizen sehr langsam. `LUsolve` ist die gespeicherte Form des
Gauß-Verfahrens — für lineare Systeme das richtige Werkzeug.

**Was tun `together` und `cancel`?** Die rohe LU-Ausgabe besteht aus ineinander verschachtelten
Brüchen. `together` fasst alles zu **einem einzigen Bruch** zusammen, `cancel` kürzt gemeinsame
Faktoren. Ergebnis: eine lesbare Übertragungsfunktion, etwa `V1/(C1*R1*s + 1)`.

**Verzögerte Auswertung:** `if self.T.rows == 0: self.buildEquationsSystem()` — ist das Tableau
noch nicht aufgebaut, geschieht das hier. Der Anwender muss `buildEquationsSystem()` nicht
selbst aufrufen.

```python
def solve(self, unknown_variable: str, input_modification: list = None,
          simplify: bool = True):
    """Return the symbolic solution of the equation system.

    Args:
        unknown_variable (str): variable for which to solve the system.
            Branch quantities like "I_R1" and "U_R1" are read straight out
            of the solution vector, node potentials like "V_2" are
            recovered from the tree afterwards.
        input_modification (list): optional replacement right hand side.
        simplify (bool): cancel the result into a single fraction.

    Returns:
        sympy.Expr: symbolic solution.

    """
    if input_modification is None:
        input_modification = []

    if self.T.rows == 0:
        self.buildEquationsSystem()

    rhs = self._resolve_rhs(input_modification)
    solution = self.T.LUsolve(rhs)

    node_name = self._is_node_request(unknown_variable)
    if node_name is not None:
        result = self._node_potential_expression(node_name, solution)
    else:
        result = solution[self._index_of(unknown_variable)]

    return sp.cancel(sp.together(result)) if simplify else result
```

---

## 4.23 `solveAll` — alle Unbekannten auf einmal

**Aufgabe:** löst das System **einmal** und gibt alle 2b Größen als Wörterbuch zurück, auf
Wunsch samt der Knotenpotentiale.

**Warum eine eigene Funktion?** `solve` 2b-mal aufzurufen hieße, das System 2b-mal zu lösen.
Dabei liefert `LUsolve` ohnehin den gesamten Vektor — man muss ihn nur auslesen. Beim
symbolischen Rechnen ist das der Unterschied zwischen Minuten und Sekunden.

`zip(self.get_unknowns(), solution)` paart Symbolnamen mit Werten.
`if index == 0: continue` überspringt die Masse (ihr Potential ist definitionsgemäß null).

```python
def solveAll(self, input_modification: list = None, include_nodes: bool = True):
    """Solve the system for every unknown at once.

    Args:
        input_modification (list): optional replacement right hand side.
        include_nodes (bool): also add the recovered node potentials.

    Returns:
        dict: mapping from symbol to symbolic solution.

    """
    if input_modification is None:
        input_modification = []

    if self.T.rows == 0:
        self.buildEquationsSystem()

    solution = self.T.LUsolve(self._resolve_rhs(input_modification))

    self.sym_result = {
        symbol: sp.cancel(sp.together(value))
        for symbol, value in zip(self.get_unknowns(), solution)
    }

    if include_nodes:
        for node_name, index in self.node_map.items():
            if index == 0:
                continue
            expression = self._node_potential_expression(node_name, solution)
            self.sym_result[sp.Symbol(f"V_{node_name}")] = sp.cancel(
                sp.together(expression))

    return self.sym_result
```

---

## 4.24 `solveNumerical` — Frequenzgang (Bode)

**Aufgabe:** löst das System numerisch für eine Liste von Frequenzen.

**Die Mathematik:** im stationären Sinuszustand gilt

$$ s \;\rightarrow\; j\omega \;=\; j\,2\pi f $$

**Eine dreistufige Beschleunigung — lohnt sich zu erwähnen:**

1. `toNumerical(...)` — alle Bauelementsymbole werden durch Zahlen ersetzt. Symbolisch bleibt
   **nur `s`**.
2. `lambdify(...)` — der SymPy-Ausdruck wird in eine echte Python/NumPy-Funktion
   **übersetzt**. (C-Analogie: eine Formel einmal kompilieren statt sie jedes Mal zu
   interpretieren.)
3. Frequenzschleife — für jedes `f` wird `s = j·2πf` eingesetzt und mit SciPy gelöst.

Dieser Weg wurde gewählt, statt symbolisch zu lösen und danach Zahlen einzusetzen, weil der
symbolische Ausdruck bei großen Netzwerken explodieren kann; hier wird pro Frequenz nur ein
kleines numerisches System gelöst.

**Robustheit:** eine singuläre Matrix (etwa exakt in einer Polstelle) wirft `LinAlgError`; der
Code stürzt nicht ab, sondern trägt `NaN` ein und läuft weiter.

Wird ein Knotenpotential angefragt, wird innerhalb der Schleife die gewichtete Summe gebildet
(das numerische Gegenstück zu §4.21).

```python
def solveNumerical(self, frequencies: list, unknown_variable: str,
                   input_modification: list = None):
    """Solve the equation system numerically over a list of frequencies.

    Args:
        frequencies (list): frequencies in Hz for which to solve.
        unknown_variable (str): variable for which to solve the system.
        input_modification (list): optional replacement right hand side.

    Returns:
        H (array): array with numerical solutions, one per frequency.

    """
    if input_modification is None:
        input_modification = []

    if self.T.rows == 0:
        self.buildEquationsSystem()

    rhs = self._resolve_rhs(input_modification)

    node_name = self._is_node_request(unknown_variable)
    if node_name is None:
        index = self._index_of(unknown_variable)
        coefficients = None
    else:
        index = None
        coefficients = self.node_potential_coeffs[node_name]

    T_num = self.toNumerical(sp.Matrix(self.T), self.value_dict)
    rhs_num = self.toNumerical(sp.Matrix(rhs), self.value_dict)

    T_func = sp.lambdify(self.s, T_num, "numpy", dummify=True)
    rhs_func = sp.lambdify(self.s, rhs_num, "numpy", dummify=True)

    def solve_freq(freq):
        jw = 1j * 2 * np.pi * freq
        try:
            x = sla.solve(
                np.array(T_func(jw), dtype=complex),
                np.array(rhs_func(jw), dtype=complex).reshape(-1),
            )
        except sla.LinAlgError:
            return np.nan

        if index is not None:
            return x[index]

        total = 0j
        for twig, coeff in coefficients.items():
            total += coeff * x[twig]
        return total

    self.num_result = np.array([solve_freq(freq) for freq in frequencies])
    return self.num_result
```

---
---

# TEIL 5 — DURCHGERECHNETES BEISPIEL: RC-TIEFPASS

**Netzliste:** `V1 (1→0)`, `R1 (1→2)`, `C1 (2→0)`

### Schritte 1–2: Knoten und Zweige
- Knoten: 0 (Masse), 1, 2 → `n − 1 = 2`
- Zweige: `b = 3` → **Zahl der Unbekannten 2b = 6**
- Maschen: `l = 3 − 2 = 1`

### Schritt 3: Baum über Union-Find (in Netzlistenreihenfolge)

| j | Zweig | Ergebnis der Vereinigung | Klasse |
|---|---|---|---|
| 0 | V1 (1,0) | 1 und 0 waren getrennt → vereinigt | **Baumzweig** |
| 1 | R1 (1,2) | 1 und 2 waren getrennt → vereinigt | **Baumzweig** |
| 2 | C1 (2,0) | bereits verbunden | **Verbindungszweig** |

Kontrolle: 2 Baumzweige = `n − 1` ✔ · 1 Verbindungszweig = `l` ✔

### Schritt 4: Baumpotentiale (BFS von der Masse)
- `e_1 = +u_V1`
- `e_2 = +u_V1 − u_R1`

### Schritt 5: Blöcke A und B (Spalten: V1, R1, C1)

```
A = [  1   1   0 ]     Knoten 1:   i_V1 + i_R1 = 0
    [  0  −1   1 ]     Knoten 2:  −i_R1 + i_C1 = 0

B = [ −1   1   1 ]     Masche:    −u_V1 + u_R1 + u_C1 = 0
```

Herleitung von B: Verbindungszweig C1 (p=2, n=0) →
`+1` in der eigenen Spalte, `− e_2 = −(u_V1 − u_R1)` → `−1` und `+1`, `+ e_0 = 0`.

### Schritte 6–7: das vollständige System, `x = [u_V1, u_R1, u_C1, i_V1, i_R1, i_C1]ᵀ`

```
┌ −1   1     1  │  0   0   0 ┐   ┌ u_V1 ┐   ┌  0 ┐   KVL (Masche)
│  0   0     0  │  1   1   0 │   │ u_R1 │   │  0 │   KCL Knoten 1
│  0   0     0  │  0  −1   1 │   │ u_C1 │   │  0 │   KCL Knoten 2
│  1   0     0  │  0   0   0 │ · │ i_V1 │ = │ V1 │   V1:  u = V1
│  0  −1     0  │  0  R1   0 │   │ i_R1 │   │  0 │   R1:  R·i − u = 0
└  0   0   sC1  │  0   0  −1 ┘   └ i_C1 ┘   └  0 ┘   C1:  sC·u − i = 0
```

### Schritt 8: Lösung (Ausgabe von `T.LUsolve(RHS)`)

$$ u_{C1} = \frac{V_1}{1 + sR_1C_1}, \qquad
   u_{R1} = \frac{sR_1C_1\,V_1}{1 + sR_1C_1}, \qquad
   i_{R1} = i_{C1} = \frac{sC_1V_1}{1 + sR_1C_1}, \qquad
   i_{V1} = -\,\frac{sC_1V_1}{1 + sR_1C_1} $$

### Nachbearbeitung: Knotenpotential

$$ V_2 \;=\; e_2 \;=\; u_{V1} - u_{R1} \;=\; \frac{V_1}{1 + sR_1C_1} $$

Die klassische Übertragungsfunktion eines RC-Tiefpasses. **Das Ergebnis stimmt.** ✔

---
---

# TEIL 6 — VERIFIKATION

Die Korrektheit des Codes wurde auf drei unabhängigen Wegen geprüft:

1. **Topologische Identität:** `A · Bᵀ = 0` (Tellegen-Orthogonalität) — muss bei jedem
   Netzwerk gelten
2. **Kreuzvalidierung:** Vergleich mit den Lösungen desselben Netzwerks aus MNA und
   erweiterter STA
3. **Unit-Tests:** 55 Tests — alle bestanden

Zusätzlich sind strukturelle Prüfungen fest im Code verankert:
- keine Masse → `ValueError`
- Zahl der Baumzweige ≠ `n−1` → Graph nicht zusammenhängend → `ValueError`
- nicht unterstützter Elementtyp → `ValueError`
- gesteuerte Quelle mit weniger als vier Anschlüssen → `ValueError`

---

# TEIL 7 — MÖGLICHE FRAGEN

**F: Sind 2b Gleichungen nicht zu viel?**
A: Mehr als bei MNA, ja. Aber die Matrix ist dünnbesetzt; der LU-Löser beschäftigt sich nicht
mit Nullen. Im Gegenzug gewinnen wir strukturelle Transparenz und bruchfreie Symbole.

**F: Ändert die Wahl des Baumes das Ergebnis?**
A: Nein. Ein anderer Baum → ein anderes, aber äquivalentes B. `A·Bᵀ = 0` gilt weiterhin, die
Lösung bleibt gleich. Nur die ausgegebenen KVL-Zeilen sehen anders aus.

**F: Warum ist `self.n` nicht die Knotenzahl?**
A: `self.n = len(node_map) - 1`, also das `n−1` der Vorlesung. Da die Massezeile aus A
gestrichen wird, ist es praktischer, direkt die Zeilenzahl von A zu führen.

**F: Warum lautet die Kondensatorgleichung `sC·u − i = 0`?**
A: `1/(sC)` ist bei DC (`s=0`) nicht definiert und macht die Matrix singulär. In der
Admittanzform gibt es keine Division.

**F: Warum belegt eine gesteuerte Quelle zwei Zweige?**
A: Weil sie zwei Tore hat und jedes Tor ein Spannungs-Strom-Paar trägt. Auch das Steuertor
muss eine Gleichung liefern (Leerlauf oder Kurzschluss), sonst wäre das System nicht
quadratisch.

**F: Warum wurde die Reihenfolge von Insydes nachgebildet?**
A: Für die Korrektheit ist das nicht nötig, wohl aber für den **Vergleich**. Zwei in derselben
Reihenfolge erzeugte Matrizen lassen sich Zeile für Zeile gegenüberstellen; das hat die
Fehlersuche erheblich beschleunigt.

---

# TEIL 8 — GLOSSAR (DE / TR / EN)

| Deutsch | Türkçe | English |
|---|---|---|
| Knoten | düğüm | node |
| Zweig | dal | branch |
| Masche | çevre / göz | loop / mesh |
| Spannbaum | kapsayan ağaç | spanning tree |
| Baumzweig | ağaç dalı | twig |
| Verbindungszweig / Sehne | bağlantı dalı | link / chord |
| Inzidenzmatrix | insidans matrisi | incidence matrix |
| Fundamentalmaschenmatrix | temel çevre matrisi | fundamental loop matrix |
| Knotensatz (KCL) | düğüm denklemi (KAY) | Kirchhoff's current law |
| Maschensatz (KVL) | çevre denklemi (KGY) | Kirchhoff's voltage law |
| Bauelementgleichung | eleman denklemi | element equation |
| Bezugsknoten / Masse | referans düğüm / toprak | reference node / ground |
| Impedanz / Admittanz | empedans / admitans | impedance / admittance |
| unabhängige Quelle | bağımsız kaynak | independent source |
| gesteuerte Quelle | kontrollü kaynak | controlled source |
| dünnbesetzte Matrix | seyrek matris | sparse matrix |
| Unbekanntenvektor | bilinmeyen vektörü | unknown vector |
| rechte Seite | sağ taraf | right hand side |
| Stempel | damga | stamp |
