import dearpygui.dearpygui as dpg
from typing import List
from plyer import filechooser


class Window:
    def __init__(self, title : str="Not Defined", width:int=800, height:int=600, autosize:bool=True, no_resize:bool=False):
        self.title : str = title
        self.id:str = ""
        self.width:int = width
        self.height:int = height
        self.autosize:bool = autosize
        self.no_resize:bool = no_resize

    def setup(self, show_menu_bar=False):
        with dpg.window(
            tag=self.title,
            on_close=self.on_close,
            menubar=show_menu_bar,
            autosize=self.autosize,
            no_resize=self.no_resize
        ) as self.id:
            self.build()
        pass

    def build(self):
        pass

    def uuid(self, tag: str) -> str:
        return f"{self.id}_" + tag
    
    def update(self):
        pass

    def open_file_dialog(self, title:str, file_extensions:List[tuple[str, str]], open_mode: bool = True) -> List[str]:

        if open_mode:
            return filechooser.open_file(title=title, filters=file_extensions)
        else:
            return filechooser.save_file(title=title, filters=file_extensions)

    def on_close(self, sender, app_data, user_data):
        # sender is the window tag
        if dpg.does_item_exist(sender):
            dpg.delete_item(sender)

        # clear internal reference
        self.id = ""
