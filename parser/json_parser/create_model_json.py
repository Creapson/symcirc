import json

def create_model_json(model_name, external_nodes, all_nodes, spice_lines):
    model_data = {
        "name": model_name,
        "netlist_file_path": "",
        "params": {},
        "inner_connecting_nodes": external_nodes,
        "nodes": all_nodes,
        "elements": [],
        "models": {},
        "subcircuits": {},
        "separator": "_"
    }

    for line in spice_lines:
        parts = line.strip().split()
        if not parts or line.startswith('*'): 
            continue

        comp_name = parts[0]
        
        if comp_name.startswith('R') or comp_name.startswith('C'):
            node1, node2, val = parts[1], parts[2], parts[3]
            comp_type = comp_name[0].upper()
            
            element = {
                "name": comp_name,
                "historical_name": comp_name,
                "symbol": val.lower(),
                "connections": [node1, node2],
                "type": comp_type,
                "params": { "value_dc": val.lower() }
            }
            model_data["elements"].append(element)
            
        elif comp_name.startswith('G'):
            n_out_plus, n_out_minus, n_ctrl_plus, n_ctrl_minus, val = parts[1:6]
            
            element = {
                "name": comp_name,
                "historical_name": comp_name,
                "symbol": val.lower(),
                "connections": [n_out_plus, n_out_minus, n_ctrl_plus, n_ctrl_minus],
                "type": "G",
                "params": { "value": val.lower() }
            }
            model_data["elements"].append(element)

    filename = f"{model_name}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(model_data, f, indent=4)
    
    print(f"[{filename}] successfully created!")


mosfet_simplified_spice = [
    "R_ds D S rds",
    "C_gd G D cgd",
    "C_gs G S cgs",
    "C_bd D B cbd",
    "C_bs S B cbs",
    "G_m D S G S gm",
    "G_mb D S B S gmb",
    "R_bd B D rbd",
    "R_bs B S rbs"
]

create_model_json(
    model_name="MOSFET_simplifiedmodel",
    external_nodes=["D", "G", "S", "B"],
    all_nodes=["D", "G", "S", "B"],
    spice_lines=mosfet_simplified_spice
)