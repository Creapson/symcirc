import dearpygui.dearpygui as dpg
from gui.windows.Window import Window
from netlist.Circuit import Circuit
from netlist.Element import Element 
from gui.components.Table import Table, Widget_Type
from netlist.Model import Model

from typing import Dict


class CircuitEditor(Window):
    def __init__(self, circuit : Circuit, parent_tag:str):
        self.circuit = circuit

        self.tables: Dict[str,  Table] = {}

        super().__init__(title=str(parent_tag + ":CircuitEditor"), autosize=False)
        pass

    def export_callback(self, sender, app_data):
        print(app_data)
        try:
            file_path:str = app_data.get("file_path_name")
            if not file_path:
                print("No file selected")
                return

            # Ensure .json extension
            if not file_path.endswith(".json"):
                file_path += ".json"

            # Dump Pydantic object to JSON
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.circuit.model_dump_json(indent=4))

            print(f"Saved to {file_path}")

        except Exception as e:
            print("Error saving file:", e)

    def build(self):
        if not dpg.does_item_exist(self.uuid("export_file_dialog")):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.export_callback,
                tag=self.uuid("export_file_dialog"),
                width=700,
                height=400,
            ):
                dpg.add_file_extension(".json")

        with dpg.menu_bar():
            with dpg.menu(label="Edit"):
                dpg.add_menu_item(
                        label="Export", 
                        enabled=True, 
                        callback=lambda: dpg.show_item(self.uuid("export_file_dialog"))
                )

        self.show_circuit(circuit=self.circuit, tag="")

        with dpg.group(horizontal=True):
            dpg.add_button(label="Save", callback=self.on_save)
            dpg.add_button(label="Close", callback=self.on_close)

    def on_close(self, sender, app_data=None, user_data=None):
        super().on_close(sender, app_data, user_data)

    def on_save(self):
        self.save_circuit(self.circuit, "")
        self.circuit.to_ai_string()
        self.on_close(self.id)

    def save_circuit(self, circuit:Circuit, tag:str):
        new_tag = tag + ":" + circuit.name
        self.save_info(circuit, new_tag)
        self.save_models(circuit.models, new_tag)
        self.save_elements(circuit.elements, new_tag)
        self.save_subcts(circuit.subcircuits, new_tag)

    def save_info(self, circuit:Circuit, tag:str):
        circuit.name = dpg.get_value(tag + ":name")
        circuit.netlist_file_path = dpg.get_value(tag + ":filepath")
        circuit.bipolar_model = dpg.get_value(tag + ":bipolar_model")
        circuit.mosfet_model = dpg.get_value(tag + ":mosfet_model")
        self.save_params(circuit.params, tag + ":params")
        circuit.inner_connecting_nodes = dpg.get_value(tag + ":inner_connecting_nodes").split(",")

    def save_params(self, params: Dict[str, str], tag:str):
        for key, _ in params.items():
            params[key] = dpg.get_value(tag + ":" + str(key))

    def save_models(self, models:dict[str, Model], tag:str):
        for name, model in models.items():
            self.save_model(model, tag + ":" + name)

    def save_model(self, model:Model, tag:str):
        model.name = dpg.get_value(tag + ":name")

    def save_elements(self, elements:list[Element], tag:str):
        table = self.tables.get(tag, None)
        if table == None: return

        for i, element in enumerate(elements):
            self.save_element(element, table, tag + ":" + str(i))

    def save_element(self, element:Element, table, tag:str):
        row_index = tag + element.name

        element.name = table.get_value(row_index, "Name", element.name)
        element.symbol  = table.get_value(row_index, "Symbol", element.symbol)
        element.historical_name = table.get_value(row_index, "Historical Name", element.historical_name)
        element.connections = table.get_value(row_index, "Connections", ",".join(element.connections)).split(",")
        element.type = table.get_value(row_index, "Type", element.type)

    def save_subcts(self, subcircuits:dict[str, Circuit], tag:str):
        for name, subct in subcircuits.items():
            self.save_circuit(subct, str(tag + ":" + name))

    def add_text_input(self, label : str, default_value:str, tag:str):
        with dpg.group(horizontal=True):
            dpg.add_text(label)
            dpg.add_input_text(default_value=default_value, tag=tag)

    def show_info(self, circuit:Circuit, tag:str):
        self.add_text_input("Name", circuit.name, tag + ":name")
        self.add_text_input("Netlist file path", circuit.netlist_file_path, tag + ":filepath")
        self.add_text_input("bipolar_model", circuit.bipolar_model, tag + ":bipolar_model")
        self.add_text_input("mosfet_model", circuit.mosfet_model, tag + ":mosfet_model")
        self.show_params(circuit.params, tag + ":params")
        self.add_text_input("Inner connecting nodes", ",".join(circuit.inner_connecting_nodes), tag + ":inner_connecting_nodes")

    def show_params(self, params: Dict[str, str], tag:str):
        for key, item in params.items():
            with dpg.group(horizontal=True):
                dpg.add_text(key)
                dpg.add_input_text(default_value=item, tag=tag + f":{key}")

    def show_elements(self, elements: list[Element], tag:str):
        if len(elements) == 0:
            return

        table = Table()
        table.setup()
        table.add_column("Name", Widget_Type.INPUT_TEXT)
        table.add_column("Symbol", Widget_Type.INPUT_TEXT)
        table.add_column("Historical Name", Widget_Type.INPUT_TEXT)
        table.add_column("Connections", Widget_Type.INPUT_TEXT)
        table.add_column("Type", Widget_Type.INPUT_TEXT)
        table.add_column("Params", Widget_Type.TEXT)

        with dpg.child_window(height=300):
            dpg.add_text("Elements:")
            for i, element in enumerate(elements):
                self.show_element(element, table, tag + ":" + str(i))
            table.build()
        self.tables[tag] = table

    def show_element(self, element: Element, table:Table, tag:str):
        row_dict = {
                "Name": element.name,
                "Symbol": element.symbol,
                "Historical Name": element.historical_name,
                "Connections": ",".join(element.connections),
                "Type": str(element.type),
                "Params": str(element.params),
                }
        table.add_row(tag + element.name, row_dict)

    def show_models(self, models: dict[str, Model], tag:str):
        if len(models) == 0:
            return
        dpg.add_text("Models:")
        with dpg.child_window(height=300):
            for name, model in models.items():
                self.show_model(model, name, tag + ":" + name)

    def show_subcts(self, sub_cts: dict[str, Circuit], tag:str):
        if len(sub_cts) == 0:
            return
        dpg.add_text("Subcirctuis:")
        with dpg.child_window(autosize_x=True):
            for name, circuit in sub_cts.items():
                self.show_circuit(circuit, tag + ":" + name)

    def show_circuit(self, circuit: Circuit, tag:str):
        new_tag = tag + ":" + circuit.name
        self.show_info(circuit, new_tag)
        self.show_elements(circuit.elements, new_tag)
        self.show_models(circuit.models, new_tag)
        self.show_subcts(circuit.subcircuits, new_tag)

    def show_model(self, model: Model, name:str, tag:str):
        with dpg.group(horizontal=True):
            dpg.add_input_text(default_value=name, width=50)
            dpg.add_input_text(default_value=model.name, tag=(tag + ":name"), width=50)
            dpg.add_text("params here!")
