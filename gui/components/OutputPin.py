import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field
from typing import Optional, Dict
from collections.abc import Callable

from enum import IntEnum

class PinType(IntEnum):
    BASE = 0
    CIRCUIT_EDIT = 1
    MNA_EDIT = 2

class OutputPin(BaseModel):
    tag: str = Field(default="")
    pin_id: int = Field(default=0)
    text: str = Field(default="")
    pin_type: PinType = Field(default=PinType.BASE)

    button_text: str = Field(default="")
    button_callback: Callable | None = Field(default=None)
    id_transition_table: Dict[int, int] = Field(default_factory=dict, exclude=True)

    def button_tag(self, par_obj):
        return par_obj.uuid(self.tag + "_button")

    def setup_pin(self, parent_id, par_obj):
        old_id = self.pin_id
        if not dpg.does_item_exist(par_obj.uuid(self.tag)):
            with dpg.node_attribute(
                parent=parent_id,
                attribute_type=dpg.mvNode_Attr_Output,
                ) as self.pin_id:
                with dpg.group(horizontal=True):
                    dpg.add_text(self.text, tag=par_obj.uuid(self.tag))

                    if self.pin_type in (PinType.CIRCUIT_EDIT, PinType.MNA_EDIT):
                        dpg.add_button(
                                label=self.button_text,
                                callback=self.button_callback,
                                tag=self.button_tag(par_obj),
                        )
        if (old_id != self.pin_id):
            self.id_transition_table[old_id] = self.pin_id

        print(f"Setup output_pin: {self.tag}")
        return self.pin_id

    def update_button(self, par_obj, button_text, button_callback):
        """Refresh label/callback of an already-created output pin's button."""
        self.button_text = button_text
        self.button_callback = button_callback

        tag = self.button_tag(par_obj)
        if dpg.does_item_exist(tag):
            dpg.configure_item(tag, label=button_text, callback=button_callback)

