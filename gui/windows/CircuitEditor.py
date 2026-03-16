import dearpygui.dearpygui as dpg
from gui.windows.Window import Window
from netlist.Circuit import Circuit
from netlist.Element import Element 
from netlist.Model import Model


class CircuitEditor(Window):
    def __init__(self, circuit : Circuit, parent_tag:str):
        self.circuit = circuit

        super().__init__(title=str(parent_tag + ":CircuitEditor"), autosize=False)
        pass

    def setup(self):
        def build():
            self.show_circuit(circuit=self.circuit, tag="")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=self.on_save)
                dpg.add_button(label="Close", callback=self.on_close)

        super().setup(build)

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
        circuit.inner_connecting_nodes = dpg.get_value(tag + ":inner_connecting_nodes").split(",")

    def save_models(self, models:dict[str, Model], tag:str):
        for name, model in models.items():
            self.save_model(model, tag + ":" + name)

    def save_model(self, model:Model, tag:str):
        model.name = dpg.get_value(tag + ":name")

    def save_elements(self, elements:list[Element], tag:str):
        for i, element in enumerate(elements):
            self.save_element(element, tag + ":" + str(i))

    def save_element(self, element:Element, tag:str):
        element.name = dpg.get_value(tag + ":name")
        element.symbol = dpg.get_value(tag + ":symbol")
        element.type = dpg.get_value(tag + ":type")
        element.connections = dpg.get_value(tag + ":connections").split(",")

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
        self.add_text_input("Inner connecting nodes", ",".join(circuit.inner_connecting_nodes), tag + ":inner_connecting_nodes")

    def show_elements(self, elements: list[Element], tag:str):
        if len(elements) == 0:
            return
        with dpg.child_window(height=300):
            dpg.add_text("Elements:")
            for i, element in enumerate(elements):
                self.show_element(element, tag + ":" + str(i))

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

    def show_element(self, element: Element, tag:str):
        with dpg.group(horizontal=True):
            dpg.add_input_text(default_value=element.name, tag=(tag + ":name"), width=50)
            dpg.add_input_text(default_value=element.get_symbol(),tag=(tag + ":symbol"), width=50)
            dpg.add_input_text(default_value=element.type,tag=(tag + ":type"), width=50)
            self.add_text_input("connections", ",".join(element.connections), tag + ":connections")

    def show_model(self, model: Model, name:str, tag:str):
        with dpg.group(horizontal=True):
            dpg.add_input_text(default_value=name, width=50)
            dpg.add_input_text(default_value=model.name, tag=(tag + ":name"), width=50)
            dpg.add_text("params here!")
