import dearpygui.dearpygui as dpg
from gui.windows.Window import Window
from pathlib import Path
import json

class StyleEditorWindow(Window):
    def __init__(self, application, current_theme="Default"):
        self.application = application
        self.styles = [
            ("seperator Main", False, [], 0, 0),
            ("mvStyleVar_WindowPadding", True, [8, 8], 0, 20),
            ("mvStyleVar_FramePadding", True, [4, 3], 0, 20),
            ("seperator Boarder", False, [], 0, 0),
            # ("mv_Borader_Test", False, [4], 0, 10),
        ]
        self.colors = [
            ("mvThemeCol_Text", [255, 255, 255, 255]),
            ("mvThemeCol_TextDisabled", [151, 151, 151, 255]),
        ]
        self.current_theme = current_theme

        self.default_theme = self.create_default_dict()
        self.saved_themes = []
        self.saved_themes.append("Default")
        self.theme_map = {}
        self.changed_settings = {}
        self.load_saved_themes()
        self.setup_theme_engine()

        # apply current_theme
        self.apply_theme(self.load_theme(current_theme))

        super().__init__(title="Custom Style Editor", autosize=False)

    def create_default_dict(self):
        default_dict = {}
        default_dict["mvStyleVar_WindowBorderSize"] = [1]
        default_dict["mvStyleVar_FrameBorderSize"] = [0]
        default_dict["mvStyleVar_PopupBorderSize"] = [1]
        for style_str, _, values, _, _ in self.styles:
            if style_str.startswith("seperator"): continue
            default_dict[style_str] = values
        for color_str, color_val in self.colors:
            default_dict[color_str] = color_val 
            pass
        return default_dict

    def load_saved_themes(self):
        base_dir = Path(__file__).resolve().parent
        themes_path = base_dir / ".." / "themes"

        self.bipolar_models = []
        if themes_path.exists():
            self.saved_themes += [f.stem for f in themes_path.iterdir() if f.is_file() and f.suffix == ".json"]
        print(self.saved_themes)

    def setup_theme_engine(self):
        with dpg.theme() as self.style_theme_id:
            with dpg.theme_component(dpg.mvAll):

                self.theme_map["mvStyleVar_WindowBorderSize"] = dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize)
                self.theme_map["mvStyleVar_FrameBorderSize"] = dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                self.theme_map["mvStyleVar_PopupBorderSize"] = dpg.add_theme_style(dpg.mvStyleVar_PopupBorderSize)
                
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
            self.changed_settings[user_data] = cleaned_val
        else:
            print(f"Engine Warning: Theme item mapping missing for {user_data}")

    def update_color(self, sender, app_data, user_data):
        theme_element_id = self.theme_map.get(user_data)
        if theme_element_id is not None:
            color_255 = [int(channel * 255) for channel in app_data]

            dpg.set_value(theme_element_id, color_255)
            self.changed_settings[user_data] = color_255
        else:
            print(f"Engine Warning: Theme color mapping missing for {user_data}")

    def save_ref(self, sender, app_data):
        theme_name = dpg.get_value(self.uuid("theme_name"))
        with open(f"gui/themes/{theme_name}.json", "w") as fp:
            json.dump(self.changed_settings, fp)
        dpg.configure_item(self.uuid("theme_selector"), default_value=theme_name)
        self.saved_themes.append(theme_name)
        print("saved theme to disk")

    def load_theme(self, theme_name:str):
        if theme_name == "Default":
            return self.default_theme        
        themes_path = f"gui/themes/{theme_name}.json"

        json1_file = open(themes_path)
        json1_str = json1_file.read()
        return json.loads(json1_str)

    def apply_theme(self, settings_dict):
        for style_element_id, values in settings_dict.items():
            theme_element_id = self.theme_map.get(style_element_id)
            dpg.set_value(theme_element_id, values)

    def revert_ref(self, sender, app_data):
        self.apply_theme(self.default_theme)
    
    def theme_select_callback(self, sender, app_data):
        self.current_theme = app_data
        self.apply_theme(self.load_theme(app_data))
        self.application.set_setting("theme", app_data)

    def on_close(self, sender, app_data, user_data):
        self.application.save_setting()
        super().on_close(sender, app_data, user_data)

    def build(self):
        dpg.add_combo(label="Theme Selector", items=self.saved_themes, default_value=self.current_theme, callback=self.theme_select_callback, tag=self.uuid("theme_selector"))
        
        # Border Boolean Checkboxes
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="WindowBorder", default_value=True, callback=lambda s, a: self.update_style(s, 1.0 if a else 0.0, "mvStyleVar_WindowBorderSize"))
            dpg.add_checkbox(label="FrameBorder", default_value=False, callback=lambda s, a: self.update_style(s, 1.0 if a else 0.0, "mvStyleVar_FrameBorderSize"))
            dpg.add_checkbox(label="PopupBorder", default_value=True, callback=lambda s, a: self.update_style(s, 1.0 if a else 0.0, "mvStyleVar_PopupBorderSize"))

        # --- Local Save/Revert Controls ---
        with dpg.group(horizontal=True):
            dpg.add_button(label="Save Settings", callback=self.save_ref)
            dpg.add_button(label="Restore Default", callback=self.revert_ref)
            dpg.add_input_text(default_value="", tag=self.uuid("theme_name"))
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

