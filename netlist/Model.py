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
    ) -> Circuit | None:
        # Merge model params and element params
        param_list = {k.lower(): v for k, v in (self.params | element_params).items()}

        if self.type in ("MOS", "NMOS") or element_type == "M":
            param_list = self._mosfet_ac_param_values(param_list)
        elif self.type in ("NPN", "PNP") or element_type == "Q":
            param_list = self._bjt_ac_param_values(param_list)

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

        # Small-signal templates often reference parameters the PSpice .OP
        # section does not emit (rc, gmu, cxs, ...) or reports as 0 (cbx,
        # cjs). Any element whose value did not resolve to a number - or
        # resolved to 0 - is negligible for this operating point:
        #   * capacitor            -> open  -> drop
        #   * controlled source    -> drop
        #   * series resistor      (port <-> internal node) -> short: merge nodes
        #   * shunt/leak resistor  (internal <-> internal) -> open  -> drop
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
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        return f if f == f and f not in (float("inf"), float("-inf")) else None

    @classmethod
    def _bjt_ac_param_values(cls, param_list: Dict[str, str]) -> Dict[str, str]:
        """Resolve the BJT small-signal symbols the way Analog Insydes'
        DoBJTSmallSignal (AC, Level 1) does.

        ModelSupport.m references:
          * RPI$ac, RO$ac, RX$ac, CBC$ac, CBE$ac, CBX$ac, CJS$ac, GM$ac come
            straight from the OPERATING POINT block (already the right names)
          * the base-collector leak GMU is a conductance -> store 1/GMU$ac
          * the ohmic RC/RE come from the model card, divided by AREA:
              Rc = RC/AREA,  Re = RE/AREA
        Only finite non-zero results are written; the degeneracy cleanup opens
        or shorts everything else, so RC/RE/RX/GMU vanish for the Basic and
        Simplified levels exactly as they do in DoBJTSmallSignal.
        """
        p = dict(param_list)
        num = cls._num_or_none

        area = num(p.get("area")) or 1.0

        gmu = num(p.get("gmu$ac"))
        if gmu is None:
            gmu = num(p.get("gmu"))
        if gmu:
            p["gmu"] = repr(1.0 / gmu)

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
        DoMOSFETSmallSignal (AC, Level 1-3) does, so the JSON templates stay
        thin and the numbers come out identical.

        ModelSupport.m references:
          * gate caps are the SUM of the bias term and the overlap term:
              Cgd = CGD$ac + CGDOV$ac,  Cgs = CGS$ac + CGSOV$ac,
              Cgb = CGB$ac + CGBOV$ac
          * the drain-source element is the small-signal conductance GDS$ac
            (our template models it as a resistor, so store 1/GDS$ac)
          * ohmic RD/RS come from the model card; if both are 0 they may be
            derived from the sheet resistance:  RD = NRD*RSH,  RS = NRS*RSH
        Only keys that resolve to a finite non-zero value are written; anything
        else is left untouched so the degeneracy cleanup opens / shorts it.
        """
        p = dict(param_list)

        def num(key):
            try:
                return float(p[key])
            except (KeyError, ValueError, TypeError):
                return None

        def put(key, value):
            if value is not None and value == value and value not in (
                    float("inf"), float("-inf")) and value != 0.0:
                p[key] = repr(value)

        cgd = (num("cgd") or 0.0) + (num("cgdov") or 0.0)
        cgs = (num("cgs") or 0.0) + (num("cgsov") or 0.0)
        cgb = (num("cgb") or 0.0) + (num("cgbov") or 0.0)
        put("cgd", cgd)
        put("cgs", cgs)
        put("cgb", cgb)

        gds = num("gds")
        if gds:
            put("rds", 1.0 / gds)

        gbd, gbs = num("gbd"), num("gbs")
        if gbd:
            put("rbd", 1.0 / gbd)
        if gbs:
            put("rbs", 1.0 / gbs)

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

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.type, self.filename, param_string)
