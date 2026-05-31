import json
import os
import sys

def main():
    sys.path.insert(0, os.path.abspath('.'))
    notebook_path = "experiments.ipynb"

    if not os.path.exists(notebook_path):
        print(f"Error: {notebook_path} does not exist.")
        sys.exit(1)
        
    print(f"Reading {notebook_path}...")
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = json.load(f)
        
    code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    print(f"Found {len(code_cells)} code cells. Executing them sequentially...")
    
    # We will execute all cells in a single global context
    global_context = {
        "__name__": "__main__",
        "__file__": os.path.abspath(notebook_path),
        "display": print
    }

    
    for i, cell in enumerate(code_cells, 1):
        source = "".join(cell["source"])
        # Mock plt.show to avoid blocking/window issues during CLI execution
        source = source.replace("plt.show()", "# plt.show()")
        
        print(f"\n--- Executing Code Cell {i}/{len(code_cells)} ---")
        try:
            exec(source, global_context)
        except Exception as e:
            print(f"Error executing cell {i}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
    print("\nNotebook execution completed successfully.")
    
    # Check if the expected output files are generated
    expected_files = [
        os.path.join("figure", "hubs_topology_combined.png"),
        os.path.join("figure", "user_coverage_distribution_combined.png"),
        os.path.join("figure", "user_distance_distribution_combined.png"),
        os.path.join("figure", "qualitative_grid_cityA.png")
    ]
    
    print("\nVerifying output files:")
    all_exist = True
    for f in expected_files:
        if os.path.exists(f):
            print(f"  [OK] {f} (size: {os.path.getsize(f)} bytes)")
        else:
            print(f"  [MISSING] {f}")
            all_exist = False
            
    if all_exist:
        print("\nAll expected plots were generated and saved successfully!")
    else:
        print("\nSome expected plots are missing.")
        sys.exit(1)

if __name__ == '__main__':
    main()
