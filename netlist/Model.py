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

    def to_ai_string(self, indent: int):
        param_string = ", ".join(f'"{k}" -> {v}' for k, v in self.params.items())
        print("\t" * indent, self.name, self.type, self.filename, param_string)
