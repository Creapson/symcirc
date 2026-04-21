import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, Annotated, Union, Tuple, Literal
from enum import IntEnum

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

    # persistent Data (this gets saved)
    label: str
    position: Tuple[float, float] = (0, 0)
    data: Dict[str, Any] = Field(default_factory=dict)
    node_type: Literal[NodeType.BASE] = NodeType.BASE    

    # non persistent data
    node_id: Union[int, str] = Field(default=None, exclude=True)
    editor: Any = Field(default=None, exclude=True)
    connections: Dict[Any, Any] = Field(default_factory=dict, exclude=True)
    output_values: Dict[Any, Any] = Field(default_factory=dict, exclude=True)
    output_pins: Dict[Any, Any] = Field(default_factory=dict, exclude=True)
    input_pins: Dict[Any, Any] = Field(default_factory=dict, exclude=True)
    do_propagation: bool = Field(default=False, exclude=True)

    def setup(self, node_editor_tag):
        with dpg.node(
            label=self.label, 
            pos=self.position, 
            parent=node_editor_tag
        ) as self.node_id:
            self.build()

        dpg.set_item_pos(self.node_id, self.position)
        return self.node_id

    def build(self):
        with self.add_static_attr():
            dpg.add_button(label="Debug Log", callback=self.debug_print)
        pass

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

    def add_output_attr(self):
        return dpg.node_attribute(
            parent=self.node_id, attribute_type=dpg.mvNode_Attr_Output
        )

    def add_output_pin_value(self, output_pin_tag, value):
        output_pin = self.output_pins.get(output_pin_tag, None)
        self.output_values[output_pin] = value

        self.editor.propagate(output_pin)
        print("Output Values", self.output_values)

    def add_connection(self, pin_id, connected_node):
        self.connections[pin_id] = connected_node
        print("Connections in Node: ", self.connections)

    def onlink_callback(self):
        if self.do_propagation:
            self.update()
        pass

    def delink_callback(self):
        pass

    def get_input_pin_value(self, input_pin_tag):
        if input_pin_tag in self.input_pins:
            input_pin = self.input_pins.get(input_pin_tag, None)
            from_pin = self.connections.get(input_pin, None)

            if from_pin is None:
                return None

            # traverse the connection to the connected node
            # and get the object from there
            from_node_id = dpg.get_item_parent(from_pin)
            from_node = self.editor.node_dic[from_node_id]
            return from_node.output_values.get(from_pin, None)

        else:
            return None

    def update(self):
        # when update is called all settings should be set
        self.do_propagation = True

    def debug_print(self):
        print(f"\n\nDebug Output from Node: {self.label}")
        print("Label: ", self.label)
        print("Position: ", self.position)
        print("NodeID: ", self.node_id)
        print("Connections: ", self.connections)
        print("Input Pins", self.input_pins)
        print("output Values: ", self.output_values)
        print("output pins: ", self.output_pins)


"""
import dearpygui.dearpygui as dpg

from gui.nodes.Node import Node

class Copy(Node):
    def setup(self, node_editor_tag):
        def build():
            pass

        return super().setup(build, node_editor_tag)

    def onlink_callback(self):
        super().onlink_callback()

    def update(self):
        super().update()
"""
