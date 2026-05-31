import pandas as pd
import numpy as np
import os
import sys

def test_fixed_mcs(mcs_val):
    sys.path.append(os.path.abspath('.'))
    from module import UniversalCascadeTracer, evaluate_clustering_quality

    results = []
    for city in ['cityA', 'cityB', 'cityC', 'cityD']:
        df = pd.read_parquet(f'data/{city}-dataset.parquet')
        df = df.dropna(subset=['x', 'y', 'd', 't'])
        
        # We can cap to 1000 users or run on all, let's run on 1000 users to see
        unique_uids = df['uid'].unique()[:1000]
        df = df[df['uid'].isin(unique_uids)].copy()
        
        for w in [3, 5, 7]:
            # Pass min_cluster_sizes as a single value wrapped in a list
            tracer = UniversalCascadeTracer(df, min_cluster_sizes=[mcs_val])
            tracer.build_universal_hubs_and_log(radius_K=1.0, smoothing_window=w)
            metrics = evaluate_clustering_quality(tracer, df)
            results.append({
                'City': city,
                'Window': w,
                'Global_Hubs': metrics['Num_Global_Hubs'],
                'Local_Hubs': metrics['Num_Local_Hubs']
            })
            
    df_res = pd.DataFrame(results)
    print(f"\n--- Results for Fixed MCS = {mcs_val} ---")
    print(df_res.to_string(index=False))

if __name__ == '__main__':
    test_fixed_mcs(10)
    test_fixed_mcs(15)
