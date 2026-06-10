import dearpygui.dearpygui as dpg
from pydantic import BaseModel, Field

from typing import Dict, Any, List
from enum import IntEnum

class Widget_Type(IntEnum):
    TEXT = 0
    COMBO = 1
    BUTTON = 2
    INPUT_INT = 3
    INPUT_FLOAT = 4
    INPUT_TEXT = 5


class Table(BaseModel):
    table_id: int = Field(default=0, exclude=True)
    is_setup: bool = Field(default=False, exclude=True)

    columns: List[tuple[str, Widget_Type, Any]] = Field(default_factory=list)
    indices: List[str] = Field(default_factory=list)

    col_ids : Dict[str, int] = Field(default_factory=dict, exclude=True)
    #         Dict[index], tuple[row_id, Dict[column, widget_id]]
    row_ids : Dict[str, tuple[int, Dict[str, int]]] = Field(default_factory=dict, exclude=True)
    #         Dict[index], Dict[column, value]]
    row_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def add_column(self, title:str, widget_type:Widget_Type, items:List[str]=[]):
        if title in self.get_columns():
            print(f"column: {title} already exists!")
            return 
        if widget_type == Widget_Type.COMBO:
            self.columns.append((title, widget_type, items))
        else:
            self.columns.append((title, widget_type, None))

    def get_columns(self) -> List[str]:
        return [col for col, _, _ in self.columns]

    def get_indices(self) -> List[str]:
        return self.indices

    def add_row(self, index:str, row_dict: Dict[str, Any]):
        if index not in self.indices: self.indices.append(index)
        self.row_data[index] = row_dict

    def get_value(self, index:str, column:str, default_value:Any) -> Any:
        return self.row_data.get(index, {}).get(column, default_value)

    def build(self):
        if self.table_id == 0:  self.setup()

        # create columns
        for title, _, _ in self.columns:
            col_id = dpg.add_table_column(label=title, parent=self.table_id)
            self.col_ids[title] = int(col_id)

        # create rows
        for index, val_dict in self.row_data.items():
            row = int(dpg.add_table_row(parent=self.table_id))
            self.row_ids[index] = (row, {})
            for column, widget_type, value in self.columns:
                widget_id: int | str = 0
                match widget_type:
                    case Widget_Type.TEXT:
                        widget_id = dpg.add_text(val_dict.get(column, ""), parent=row)
                    case Widget_Type.COMBO:
                        widget_id = dpg.add_combo(items=value, default_value=val_dict.get(column, ""), parent=row, width=-1, callback=self.combo_callback)
                    case Widget_Type.BUTTON:
                        widget_id = dpg.add_button(label=val_dict.get(column, ""), parent=row, width=-1, callback=self.button_callback)
                    case Widget_Type.INPUT_INT:
                        continue
                    case Widget_Type.INPUT_FLOAT:
                        continue
                    case Widget_Type.INPUT_TEXT:
                        widget_id = dpg.add_input_text(default_value=val_dict.get(column, ""), parent=row, width=-1, callback=self.input_text_callback)
                    case _:
                        continue
                self.row_ids[index][1][column] = int(widget_id)

        # dpg.add_button(label="Table Debug", callback=self.print_debug)

    def find_index_and_column(self, target_id: int) -> tuple[str, str]:
        for index, (row_id, columns) in self.row_ids.items():
            for column_name, widget_id in columns.items():
                if widget_id == target_id:
                    return index, column_name
        return ("", "")

    def combo_callback(self, sender, app_data):
        index, column = self.find_index_and_column(sender)
        self.row_data[index][column] = dpg.get_value(sender)

    def button_callback(self, sender, app_data):
        pass

    def input_text_callback(self, sender, app_data):
        index, column = self.find_index_and_column(sender)
        self.row_data[index][column] = dpg.get_value(sender)
        pass

    def setup(self):
        self.table_id = int(dpg.add_table(
            header_row=True,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=True,
            no_host_extendX=True,
            borders_innerV=True,
            borders_outerV=True,
            borders_outerH=True,
        ))
        self.is_setup = True

    def clear(self):
        self.indices = []
        self.row_ids = {}
        self.row_data = {}
        dpg.delete_item(self.table_id, children_only=True)

    def delete(self):
        self.clear()
        dpg.delete_item(self.table_id)

    def print_debug(self, sender, app_data):
        print("Table ID: ", self.table_id)
        print("columns: ", self.columns)
        print("indices: ", self.indices)
        print("col ids: ", self.col_ids)
        print("row_ids: ", self.row_ids)
        print("row_data: ", self.row_data)
