import dearpygui.dearpygui as dpg


class Window:
    def __init__(self, title : str="Not Defined", width:int=800, height:int=600, autosize:bool=True, no_resize:bool=False):
        self.title : str = title
        self.id:int = 0
        self.width:int = width
        self.height:int = height
        self.autosize:bool = autosize
        self.no_resize:bool = no_resize

    def setup(self, build_func, show_menu_bar=False):
        with dpg.window(
            tag=self.title,
            on_close=self.on_close,
            menubar=show_menu_bar,
            autosize=self.autosize,
            no_resize=self.no_resize
        ) as self.id:
            build_func()
        pass

    def uuid(self, tag):
        return f"{self.id}_{tag}"
    
    def update(self):
        pass

    def on_close(self, sender, app_data, user_data):
        # sender is the window tag
        if dpg.does_item_exist(sender):
            dpg.delete_item(sender)

        # clear internal reference
        self.id = None


"""
class CopyClass(Window):

    def __init__(self):
        self.title = "Copy Node"

        super().__init__(title=self.title)

    def setup(self):
        def build():
            pass

        super().setup(build)

    def on_close(self, sender, app_data, user_data):
        super().on_close(sender=sender, app_data=app_datam user_data=user_data)
"""
