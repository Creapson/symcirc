import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, Annotated, Union, Tuple, Literal, List
from enum import IntEnum

from gui.components.OutputPin import OutputPin, PinType

class NodeType(IntEnum):
    BASE = 0
    APPROXIMATOR = 1
    BODE_PLOT = 2
    FLATTEN = 3
    IMPORT_CIRCUIT = 4
    MNA = 5
    NETLIST_PARSER = 6
    NUMERIC_SOLVER= 7
    TRANSFER_FUNCTION = 8


class Node(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # persistent Data
    label: str
    position: List[int] = [0, 0]
    data: Dict[str, Any] = Field(default_factory=dict)
    node_type: Literal[NodeType.BASE] = NodeType.BASE    
    node_id: Union[int, str] = Field(default=0)

    connections: Dict[int, int] = Field(default_factory=dict)
    output_pins: Dict[str, OutputPin] = Field(default_factory=dict)
    input_pins: Dict[str, int] = Field(default_factory=dict)
    output_values: Dict[int, Any] = Field(default_factory=dict)

    # non persistent data
    editor: Any = Field(default=None, exclude=True)
    non_persistent_output_values: Dict[int, Any] = Field(default_factory=dict, exclude=True)

    do_propagation: bool = Field(default=False)
    id_transition_table: Dict[int, int] = Field(default_factory=dict, exclude=True)

    def setup(self, node_editor_tag):
        old_id = self.node_id
        self.node_id = dpg.generate_uuid()
        print(self.node_id)

        with dpg.node(
            label=self.label, 
            pos=self.position, 
            parent=node_editor_tag,
            tag=self.node_id
        ):
            self.build()

        self.id_transition_table[old_id] = self.node_id

        dpg.set_item_pos(self.node_id, self.position)

        return self.node_id

    def build(self):
        with self.add_static_attr():
            dpg.add_button(label="Debug Log", callback=self.debug_print)

        # when laoding a pipeline from file
        # create all missing output_pins
        tmp_dic = self.output_pins
        # self.output_pins = {}
        for _, output_pin in tmp_dic.items():
            output_pin.setup_pin(self.node_id, self)
            self.id_transition_table.update(output_pin.id_transition_table)

    def delete_output_pins(self):
        for pin_tag, attr_id in list(self.output_pins.items()):
            if dpg.does_item_exist(attr_id):
                dpg.delete_item(attr_id)

            self.output_values.pop(attr_id, None)

        self.output_pins.clear()

    def uuid(self, txt: str):
        return f"{self.node_id}_" + txt

    def add_input_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Input
        )

    def add_static_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Static
        )

    def add_output_attr(self, tag=0):
        if tag == 0 :
            tag = dpg.generate_uuid()

        return dpg.node_attribute(
            parent=self.node_id, 
            attribute_type=dpg.mvNode_Attr_Output,
            tag=tag,
        )

    def add_output_pin_value(self, output_pin_tag:str, value:Any, is_persistence:bool=True):
        output_pin = self.output_pins.get(output_pin_tag, None)
        if output_pin is None:
            return
        if is_persistence:
            self.output_values[output_pin.pin_id] = value
        else:
            self.non_persistent_output_values[output_pin.pin_id] = value


        self.editor.propagate(output_pin)
        print(f"Added output value to {output_pin_tag}")
        #print("Output Values", self.output_values)

    def add_output_pin(self, tag="", text="", button_callback=None, button_text=""):
        pin_type = PinType.BASE

        if button_callback is not None:
            pin_type = PinType.CIRCUIT_EDIT

        # does pin already exist
        if tag not in self.output_pins:
            out_pin = OutputPin(
                    tag=tag,
                    text=text,
                    button_text=button_text,
                    pin_type=pin_type
                    )
            out_pin.setup_pin(self.node_id, self)
            self.output_pins[tag] = out_pin

    def add_input_pin(self, tag="", text=""):
        input_pin = 0
        if not dpg.does_item_exist(self.uuid(tag)):
            with self.add_input_attr() as input_pin:
                dpg.add_text(
                    default_value=text,
                    tag=self.uuid(tag),
                )

            if tag in self.input_pins:
                self.id_transition_table[self.input_pins[tag]] = input_pin

            self.input_pins[tag] = input_pin

        print("added input pin", input_pin)
        return input_pin

    def add_connection(self, pin_id, connected_node):
        self.connections[pin_id] = connected_node
        print("Connections in Node: ", self.connections)

    def onlink_callback(self):
        if self.do_propagation:
            self.update()
        pass

    def delink_callback(self):
        pass

    def get_input_pin_value(self, input_pin_tag : str, default_value: Any = None) -> Any:
        if input_pin_tag in self.input_pins:
            input_pin = self.input_pins.get(input_pin_tag, None)
            from_pin = self.connections.get(input_pin, None)

            if input_pin is None: return default_value
            if from_pin is None: return default_value

            # traverse the connection to the connected node
            # and get the object from there
            from_node_id = dpg.get_item_parent(from_pin)
            from_node = self.editor.node_dic[from_node_id]
            output_values = from_node.output_values | from_node.non_persistent_output_values
            return output_values.get(from_pin, default_value)

        else:
            return default_value

    def update(self):
        # when the first calculation is done. We assume a change in
        # inputs doesnt mean a change in the settings

        # exceptions
        if (self.node_type == NodeType.NETLIST_PARSER): return
        if (self.node_type == NodeType.TRANSFER_FUNCTION): return

        self.do_propagation = True

    def save(self):
        self.position = dpg.get_item_pos(self.node_id)

    def debug_print(self):
        print(f"\n\nDebug Output from Node: {self.label}")
        print("Label: ", self.label)
        print("Position: ", self.position)
        print("NodeID: ", self.node_id)
        print("Connections: ", self.connections)
        print("Input Pins", self.input_pins)
        print("output Values: ", self.output_values)
        print("non_P output Values: ", self.non_persistent_output_values)
        print("output pins: ", self.output_pins)
        print("id_transition_table", self.id_transition_table)
