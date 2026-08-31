import traceback
from Modified_Node_Analysis import ModifiedNodalAnalysis

# --- Sözlüğü (Dict) Obje (Object) yapısına çeviren sarmalayıcı sınıflar ---
class MockElement:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)

class MockCircuit:
    def __init__(self, d):
        for k, v in d.items():
            if k == 'elements':
                setattr(self, k, [MockElement(e) for e in v])
            else:
                setattr(self, k, v)
# --------------------------------------------------------------------------

def run_backend_test():
    print("1. Devre veri yapısı (Obje olarak) tanımlanıyor...")
    
    circuit_dict = {
        "name": "simple_lc",
        "netlist_file_path": "C:\\Users\\Abuyl\\OneDrive\\Belgeler\\sym\\symcirc\\test_circuits\\",
        "params": {"sweep": "DEC 101 0.1 10000000.0"},
        "inner_connecting_nodes": [],
        "bipolar_model": "beta_with_r_be",
        "mosfet_model": "BSIM",
        "nodes": ["1", "2", "0", "3"],
        "elements": [
            {"name": "C1", "historical_name": "C_C1", "symbol": "", "connections": ["1", "2"], "type": "C", "params": {"value_dc": "10u"}},
            {"name": "V1", "historical_name": "V_V1", "symbol": "", "connections": ["1", "0"], "type": "V", "params": {"value_dc": "0", "value_ac": "1"}},
            {"name": "L1", "historical_name": "L_L1", "symbol": "", "connections": ["2", "3"], "type": "L", "params": {"value_dc": "2.533m"}},
            {"name": "R3", "historical_name": "R_R3", "symbol": "", "connections": ["3", "0"], "type": "R", "params": {"value_dc": "10"}}
        ],
        "models": {},
        "subcircuits": {},
        "separator": "_"
    }

    # Sözlüğü objeye dönüştür (ModifiedNodalAnalysis'in beklediği format)
    circuit_obj = MockCircuit(circuit_dict)

    try:
        print("2. MNA Sınıfı başlatılıyor...")
        mna = ModifiedNodalAnalysis(circuit_obj)
        
        print("3. MNA Matrisi kuruldu. Pole/Zero analizi tetikleniyor...")
        target_node = "V_2" 
        results = mna.get_poles_zeros(target_node)
        
        print("\n--- HESAPLAMA BAŞARILI ---")
        print(f"Zeros: {results['numeric']['zeros']}")
        print(f"Poles: {results['numeric']['poles']}")

    except Exception as e:
        print(f"\n--- HATA TESPİT EDİLDİ ---")
        print(f"Hata Türü: {type(e).__name__}")
        print(f"Açıklama: {e}")
        print("\nTraceback:")
        traceback.print_exc()

if __name__ == "__main__":
    run_backend_test()