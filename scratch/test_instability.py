import pandas as pd
import numpy as np
import os
import sys
from sklearn.cluster import HDBSCAN

def analyze_city(city_path):
    sys.path.append(os.path.abspath('.'))
    from module import UniversalCascadeTracer
    
    # Load all data or cap to see (let's load all or 1000 users like in the user's run)
    df = pd.read_parquet(city_path)
    # The user's run has local hubs = ~8000, which means they are running on ALL data!
    # Let's not cap USER_NUM to match the user's exact run!
    df = df.dropna(subset=['x', 'y', 'd', 't'])
    
    print(f"\n==================================================")
    print(f"Analyzing {os.path.basename(city_path)}")
    print(f"==================================================")
    
    mcs_list = [15, 10, 5, 3]
    
    for w in [3, 5, 7]:
        tracer = UniversalCascadeTracer(df)
        user_local_hubs, all_local_centroids, event_log_no_global, user_local_labels = tracer.build_local_hubs(w)
        coords = np.array([[c['x'], c['y']] for c in all_local_centroids])
        
        print(f"\nWindow W = {w} (centroids count: {len(coords)}):")
        
        selected_mcs = None
        for mcs in mcs_list:
            db = HDBSCAN(min_cluster_size=mcs, copy=True).fit(coords)
            unique_zones = set(db.labels_) - {-1}
            num_zones = len(unique_zones)
            print(f"  MCS = {mcs} -> found {num_zones} clusters")
            if num_zones > 1 and selected_mcs is None:
                selected_mcs = mcs
                
        print(f"  -> Dynamic selection chose MCS = {selected_mcs}")

if __name__ == '__main__':
    analyze_city('data/cityB-dataset.parquet')
    analyze_city('data/cityD-dataset.parquet')
