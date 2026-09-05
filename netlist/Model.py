from __future__ import annotations
from typing import Dict, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict
import os
from pathlib import Path

if TYPE_CHECKING:
    from netlist.Circuit import Circuit


class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    type: str = ""
    filename: str = ""
    params: Dict[str, str] = {} 

    def add_param(self, paramSymbol: str, value):
        self.params[paramSymbol] = value

    def get_generated_subcircuit(
        self,
        element_params: Dict[str, str],
        bipolar_model: str,
        mosfet_model: str,
        element_type: str = "",
        diode_model: str = "BasicDiodeModels",
        jfet_model: str = "BasicJFETModels",
    ) -> Circuit | None:
        # Merge model params and element params
        param_list = {k.lower(): v for k, v in (self.params | element_params).items()}

        # Before the transistor is replaced by its small-signal equivalent,
        # resolve the symbol -> value map the way Analog Insydes does: gate
        # cap = bias + overlap term, output element = 1/g_ds, parasitic
        # RC/RE/RD/RS from the model card, etc. This keeps the JSON template
        # thin and makes the numbers match AI term for term.
        if self.type in ("MOS", "NMOS") or element_type == "M":
            param_list = self._mosfet_ac_param_values(param_list)
        elif self.type in ("NPN", "PNP") or element_type == "Q":
            param_list = self._bjt_ac_param_values(param_list)
        elif self.type in ("NJF", "PJF") or element_type == "J":
            param_list = self._jfet_ac_param_values(param_list)
        elif self.type == "D" or element_type == "D":
            param_list = self._diode_ac_param_values(param_list)

        from netlist.Circuit import Circuit

        current_file_dir = Path(__file__).resolve().parent
        project_root = current_file_dir.parent

        # 3. Choose correct small signal model library sub-path.
        # Fall back to the element kind ("Q" = bipolar, "M" = mosfet) when the
        # .model card type is unknown - e.g. the model lives in an external
        # .lib we cannot read, but the .out still carries the small-signal params.
        if self.type in ("NPN", "PNP") or element_type == "Q":
            sub_path = Path("library/small_signal_models/bipolar_models") / f"{bipolar_model}.json"
        elif self.type in ("MOS", "NMOS") or element_type == "M":
            sub_path = Path("library/small_signal_models/mosfet_models") / f"{mosfet_model}.json"
        elif self.type in ("NJF", "PJF") or element_type == "J":
            sub_path = Path("library/small_signal_models/jfet_models") / f"{jfet_model}.json"
        elif self.type == "D" or element_type == "D":
            sub_path = Path("library/small_signal_models/diode_models") / f"{diode_model}.json"
        else:
            print(f"Failed to load model! Type: {self.type} is not known!")
            return None

        # target_model = project_root / sub_path
        target_model = sub_path

        # load small signal model from library
        with open(target_model, "r", encoding="utf-8") as f:
            json_string = f.read()
        circuit = Circuit.model_validate_json(json_string)

        # replace the str in the value slot with the numeric values
        for element in circuit.elements:
            element.remap_values(param_list)

        # DEGENERACY CLEANUP. Small-signal templates often reference
        # parameters the PSpice .OP section does not emit (rc, gmu, cxs,
        # ...) or reports as 0 (cbx, cjs). Any element whose value did not
        # resolve to a number - or resolved to 0 - is negligible for this
        # operating point:
        #   * capacitor           -> open  -> drop
        #   * controlled source   -> drop
        #   * series resistor     (port <-> internal node) -> short: merge nodes
        #   * shunt/leak resistor (internal <-> internal)   -> open  -> drop
        # All decisions are taken from the *original* template topology and
        # then applied together, so one merge cannot make another element
        # look like something it is not.
        inner = set(circuit.inner_connecting_nodes)

        def _num(v):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        merges: Dict[str, str] = {}
        survivors = []
        for element in circuit.elements:
            vkey = "value" if element.type in ("E", "G", "F", "H") else "value_dc"
            val = _num(element.params.get(vkey))
            if val is not None and val != 0.0:
                survivors.append(element)
                continue
            if element.type == "R" and len(element.connections) == 2:
                a, b = element.connections
                a_port, b_port = a in inner, b in inner
                if a_port != b_port:                      # series R -> short
                    drop_n, keep_n = (a, b) if not a_port else (b, a)
                    merges[drop_n] = keep_n
                # else: shunt/leak R (internal<->internal) -> just drop

        def canon(node: str) -> str:
            seen = set()
            while node in merges and node not in seen:
                seen.add(node)
                node = merges[node]
            return node

        for element in survivors:
            element.connections = [canon(n) for n in element.connections]
        circuit.elements = survivors
        return circuit

    @staticmethod
    def _num_or_none(value):
        """Convert a value to float; return None if it cannot be parsed or
        is not finite (nan / +-inf). Used by the AI-style formulas to ask
        "is this parameter present and a usable number?".
        """
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        return f if f == f and f not in (float("inf"), float("-inf")) else None

    @classmethod
    def _bjt_ac_param_values(cls, param_list: Dict[str, str]) -> Dict[str, str]:
        """Resolve the BJT small-signal symbols the way Analog Insydes'
             `DoBJTSmallSignal` (AC, Level 1) does.

             Per ModelSupport.m:
               * RPI$ac, RO$ac, RX$ac, CBC$ac, CBE$ac, CBX$ac, CJS$ac, GM$ac
                 come straight from the OPERATING POINT block (right names)
               * the base-collector leak GMU is a conductance -> store 1/GMU$ac
               * the ohmic RC/RE come from the model card, divided by AREA:
                 Rc = RC/AREA,  Re = RE/AREA
             Only finite non-zero results are written; the degeneracy cleanup
             opens or shorts everything else, so RC/RE/RX/GMU vanish for the
             Basic and Simplified levels exactly as the simp==1 / simp==2
             rules in `DoBJTSmallSignal` prescribe.
        """
        p = dict(param_list)
        num = cls._num_or_none

        # AREA defaults to 1 (unit area).
        area = num(p.get("area")) or 1.0

        # GMU is a conductance -> store it as the resistance 1/GMU. Most
        # PSpice .out files have no GMU, in which case the element is dropped.
        gmu = num(p.get("gmu$ac"))
        if gmu is None:
            gmu = num(p.get("gmu"))
        if gmu:
            p["gmu"] = repr(1.0 / gmu)

        # Ohmic base/collector/emitter parasitics from the model card,
        # divided by AREA.
        rc = num(p.get("rc"))
        if rc:
            p["rc"] = repr(rc / area)
        re_ = num(p.get("re"))
        if re_:
            p["re"] = repr(re_ / area)

        return p

    @staticmethod
    def _mosfet_ac_param_values(param_list: Dict[str, str]) -> Dict[str, str]:
        """Resolve the MOSFET small-signal symbols the way Analog Insydes'
             `DoMOSFETSmallSignal` (AC, Level 1-3) does, so the JSON templates
             stay thin and the numbers come out identical.

             Per ModelSupport.m:
               * gate caps are the SUM of the bias term and the overlap term:
                 Cgd = CGD$ac + CGDOV$ac,  Cgs = CGS$ac + CGSOV$ac,
                 Cgb = CGB$ac + CGBOV$ac
               * the drain-source element is the small-signal conductance GDS$ac
                 (our template models it as a resistor, so store 1/GDS$ac)
               * ohmic RD/RS come from the model card; if both are 0 they may be
                 derived from the sheet resistance:  RD = NRD*RSH,  RS = NRS*RSH
             Only keys that resolve to a finite non-zero value are written;
             anything else is left untouched so the degeneracy cleanup
             opens / shorts it.
        """
        p = dict(param_list)

        def num(key):
            # parse p[key] to float, else None.
            try:
                return float(p[key])
            except (KeyError, ValueError, TypeError):
                return None

        def put(key, value):
            # Write the result into the map only if it is finite and
            # non-zero; otherwise leave it, so the element is dropped by
            # the cleanup step.
            if value is not None and value == value and value not in (
                    float("inf"), float("-inf")) and value != 0.0:
                p[key] = repr(value)

        # Gate caps: bias + overlap term, summed.
        cgd = (num("cgd") or 0.0) + (num("cgdov") or 0.0)
        cgs = (num("cgs") or 0.0) + (num("cgsov") or 0.0)
        cgb = (num("cgb") or 0.0) + (num("cgbov") or 0.0)
        put("cgd", cgd)
        put("cgs", cgs)
        put("cgb", cgb)

        # D-S conductance -> resistance 1/GDS.
        gds = num("gds")
        if gds:
            put("rds", 1.0 / gds)

        # Bulk-junction leak conductances -> resistance.
        gbd, gbs = num("gbd"), num("gbs")
        if gbd:
            put("rbd", 1.0 / gbd)
        if gbs:
            put("rbs", 1.0 / gbs)

        # Ohmic RD/RS from the model card; if both 0, from sheet resistance.
        rd = num("rd") or 0.0
        rs = num("rs") or 0.0
        if rd == 0.0 and rs == 0.0:
            nrd, nrs, rsh = num("nrd") or 0.0, num("nrs") or 0.0, num("rsh") or 0.0
            if nrd > 0.0:
                rd = nrd * rsh
            if nrs > 0.0:
                rs = nrs * rsh
        put("rd", rd)
        put("rs", rs)

        return p

    @classmethod
    def _diode_ac_param_values(cls, param_list: Dict[str, str]) -> Dict[str, str]:
        """Resolve the diode small-signal symbols the way Analog Insydes'
             `DoDiodeSmallSignal` does.

             Per ModelSupport.m:
               * REQ$ac (small-signal resistance = 1/g_d) and CAP$ac (barrier +
                 diffusion capacitance) come straight from the OPERATING POINT
                 block
               * the ohmic series RS comes from the model card, divided by AREA:
                 Rs = RS/AREA  (Full level only)
             When RS is absent the R_s element does not resolve and the
             degeneracy cleanup shorts A to AS - the Full model collapses to
             Basic exactly as simp>0 prescribes.
        """
        p = dict(param_list)
        num = cls._num_or_none

        area = num(p.get("area")) or 1.0
        rs = num(p.get("rs"))
        if rs:
            p["rs"] = repr(rs / area)
        return p

    @classmethod
    def _jfet_ac_param_values(cls, param_list: Dict[str, str]) -> Dict[str, str]:
        """Resolve the JFET small-signal symbols the way Analog Insydes'
             `DoJFETSmallSignal` (AC, Level 1) does.

             Per ModelSupport.m:
               * CGD$ac, CGS$ac, GM$ac come straight from the OPERATING POINT block
               * the drain-source element is the small-signal conductance GDS$ac;
                 our template models it as a resistor -> store R_ds = 1/GDS$ac
               * the gate-channel junction leaks GGD$ac / GGS$ac are conductances
                 -> R_gd = 1/GGD$ac, R_gs = 1/GGS$ac (Simplified/Full; most .out
                 files omit them, then the cleanup drops the resistors)
               * the ohmic RD/RS come from the model card, divided by AREA (Full)
             Only finite non-zero results are written; the rest is left for the
             degeneracy cleanup, so the Basic/Simplified/Full levels behave
             exactly like simp==2 / simp==1 / simp==0 in `DoJFETSmallSignal`.
        """
        p = dict(param_list)
        num = cls._num_or_none

        area = num(p.get("area")) or 1.0

        gds = num(p.get("gds$ac"))
        if gds is None:
            gds = num(p.get("gds"))
        if gds:
            p["rds"] = repr(1.0 / gds)

        ggd = num(p.get("ggd$ac"))
        if ggd is None:
            ggd = num(p.get("ggd"))
        if ggd:
            p["rgd"] = repr(1.0 / ggd)

        ggs = num(p.get("ggs$ac"))
        if ggs is None:
            ggs = num(p.get("ggs"))
        if ggs:
            p["rgs"] = repr(1.0 / ggs)

        rd = num(p.get("rd"))
        if rd:
            p["rd"] = repr(rd / area)
        rs = num(p.get("rs"))
        if rs:
            p["rs"] = repr(rs / area)
        return p

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.type, self.filename, param_string)
