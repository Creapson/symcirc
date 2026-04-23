import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, Union, Tuple, Annotated

from gui.components.node_editor.nodes.Node import Node

from gui.components.node_editor.nodes.ApproximatorNode import ApproximatorNode
from gui.components.node_editor.nodes.BodePlot import BodePlot
from gui.components.node_editor.nodes.Flatten import FlattenNode
from gui.components.node_editor.nodes.ImportCircuit import ImportCircuit
from gui.components.node_editor.nodes.ModifiedNodalAnalysis import ModifiedNodalAnalysis
from gui.components.node_editor.nodes.NetlistParserNode import NetlistParserNode
from gui.components.node_editor.nodes.NumericSolver import NumericSolver
from gui.components.node_editor.nodes.TransferFunctionNode import TransferFunctionNode

AnyNode = Annotated[
    Union[Node,
          ApproximatorNode,
          BodePlot,
          FlattenNode,
          ImportCircuit,
          ModifiedNodalAnalysis,
          NetlistParserNode,
          NumericSolver,
          TransferFunctionNode
          ], 
    Field(discriminator='node_type')
]

class NodeEditor(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str = "Node Editor"
    node_dic: Dict[int, AnyNode] = Field(default_factory=dict)
    links: Dict[int, Tuple[int, int]] = Field(default_factory=dict)
    application: Any = Field(default=None, exclude=True)

    def save(self):
        for _, node in self.node_dic.items():
            node.save()

    def add_node(self, node_editor_tag, node_constructor, label, pos):
        node = node_constructor(editor=self, label=label, position=pos)

        node_id = node.setup(node_editor_tag=node_editor_tag)
        self.node_dic[node_id] = node

        return node

    def add_link(self, from_pin, to_pin):
        return dpg.add_node_link(from_pin, to_pin, parent=self.application)

    # callback runs when user attempts to connect pins
    def onlink_callback(self, sender, app_data):
        from_pin, to_pin = app_data
        to_node_id = dpg.get_item_parent(to_pin)
        to_node = self.node_dic[to_node_id]

        # you can not connect multiple outputs to one input
        # check if the input pin already has a connection
        if to_pin not in to_node.connections:
            to_node.add_connection(to_pin, from_pin)
            try:
                to_node.onlink_callback()  # may raise
            except Exception as e:
                to_node.connections = {}
                print(f"Link rejected: {e}")
                return

            link_id = dpg.add_node_link(from_pin, to_pin, parent=sender)
            # store link metadata
            self.links[link_id] = (from_pin, to_pin)

            print("Added Connections: ", app_data)

    # callback runs when user attempts to disconnect pins
    def delink_callback(self, sender, app_data):
        link_id = app_data

        if link_id not in self.links:
            return

        from_pin, to_pin = self.links[link_id]

        from_node_id = dpg.get_item_parent(from_pin)
        to_node_id = dpg.get_item_parent(to_pin)

        from_node = self.node_dic[from_node_id]
        to_node = self.node_dic[to_node_id]

        # remove logical connections
        from_node.connections.pop(from_pin, None)
        to_node.connections.pop(to_pin, None)

        to_node.delink_callback()

        # remove stored link
        del self.links[link_id]

        # remove visual link
        dpg.delete_item(link_id)

        print("Removed connection:", from_pin, "->", to_pin)

    # when the output changes run onlink_callback on
    # all connected nodes to update the value
    def propagate(self, output_pin_id):
        for link_id, (from_pin, to_pin) in self.links.items():
            if from_pin == output_pin_id:
                # get the node which should be
                # updated
                to_node_id = dpg.get_item_parent(to_pin)
                to_node = self.node_dic[to_node_id]
                to_node.onlink_callback()
