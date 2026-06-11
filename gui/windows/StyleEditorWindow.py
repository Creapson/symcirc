from re import split
import dearpygui.dearpygui as dpg
from sympy import use
from gui.windows.Window import Window

class StyleEditorWindow(Window):
    def __init__(self):
        self.styles = [
            ("seperator Main", False, [], 0, 0),
            ("mvStyleVar_WindowPadding", False, [8, 8], 0, 20),
            ("mvStyleVar_FramePadding", False, [4, 3], 0, 20),
            ("seperator Boarder", False, [], 0, 0),
            # ("mv_Borader_Test", False, [4], 0, 10),
        ]
        self.colors = [
            ("mvThemeCol_Text", (255, 255, 255, 255)),
            ("mvThemeCol_TextDisabled", (151, 151, 151, 255)),
        ]

        self.theme_map = {}
        self.setup_theme_engine()

        super().__init__(title="Custom Style Editor", autosize=False)

    def setup_theme_engine(self):
        with dpg.theme() as self.style_theme_id:
            with dpg.theme_component(dpg.mvAll):
                
                for style_str, _, values, _, _ in self.styles:
                    if style_str.startswith("seperator"):
                        continue
                    
                    dpg_constant = getattr(dpg, style_str)
                    
                    val_x = values[0]
                    val_y = values[1] if len(values) > 1 else -1.0
                    
                    self.theme_map[style_str] = dpg.add_theme_style(dpg_constant, x=val_x, y=val_y)

                for color_str, color_val in self.colors:
                    dpg_constant = getattr(dpg, color_str)
                    self.theme_map[color_str] = dpg.add_theme_color(dpg_constant, color_val)
                    
        dpg.bind_theme(self.style_theme_id)
        print(self.theme_map)

    def help_marker(self, text):
        dpg.add_text("(?)", color=(0, 255, 0, 150))
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(text, wrap=300)

    def update_style(self, sender, app_data, user_data):
        theme_element_id = self.theme_map.get(user_data)

        if theme_element_id is not None:
            slider_size = dpg.get_item_configuration(sender).get("size", 1)
            cleaned_val = app_data[:slider_size] if isinstance(app_data, list) else [app_data]
            dpg.set_value(theme_element_id, value=cleaned_val)
        else:
            print(f"Engine Warning: Theme item mapping missing for {user_data}")

    def update_color(self, sender, app_data, user_data):
        theme_element_id = self.theme_map.get(user_data)
        if theme_element_id is not None:
            color_255 = [int(channel * 255) for channel in app_data]

            dpg.set_value(theme_element_id, color_255)
        else:
            print(f"Engine Warning: Theme color mapping missing for {user_data}")

    def save_ref(self):
        print("Save not implemented yet!")


    def revert_ref(self):
        print("Restore not implemented yet!")

    def build(self):
        dpg.add_combo(label="Theme Selector", items=["This", "is", "Currently", "Empty"], default_value="Empty")
        
        # Border Boolean Checkboxes
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="WindowBorder", default_value=True, callback=lambda s, a: self.update_style(s, 1.0 if a else 0.0, "WindowBorderSize"))
            dpg.add_checkbox(label="FrameBorder", default_value=False, callback=lambda s, a: self.update_style(s, 1.0 if a else 0.0, "FrameBorderSize"))
            dpg.add_checkbox(label="PopupBorder", default_value=True, callback=lambda s, a: self.update_style(s, 1.0 if a else 0.0, "PopupBorderSize"))

        # --- Local Save/Revert Controls ---
        with dpg.group(horizontal=True):
            dpg.add_button(label="Save Settings", callback=self.save_ref)
            dpg.add_button(label="Restore Default", callback=self.revert_ref)
            dpg.add_input_text(default_value="")
            self.help_marker("Save/Restore the current Settings")
        
        dpg.add_separator()
        with dpg.tab_bar():
            with dpg.tab(label="Styles"):
                for style_str, is_int, values, min, max in self.styles:
                    if style_str.startswith("seperator"):
                        name = style_str.split()[1]
                        dpg.add_text(name)
                        dpg.add_separator()
                        pass
                    else:
                        if is_int:
                            dpg.add_slider_intx(
                                    label=style_str, 
                                    size=len(values), 
                                    min_value=min, 
                                    max_value=max,
                                    callback=self.update_style,
                                    user_data=style_str,
                                    default_value=values,
                            )
                        else:
                            dpg.add_slider_floatx(
                                    label=style_str, 
                                    size=len(values), 
                                    min_value=min, 
                                    max_value=max,
                                    callback=self.update_style,
                                    user_data=style_str,
                                    default_value=values,
                            )

            with dpg.tab(label="Colors"):
                for color_str, color_val in self.colors:
                    dpg.add_color_edit(
                        label=color_str,
                        default_value=color_val,
                        callback=self.update_color,
                        user_data=color_str
                    )

    def update(self):
        pass

