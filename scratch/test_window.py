import pandas as pd
import numpy as np
import os
import sys

def main():
    sys.path.append(os.path.abspath('.'))
    from module import UniversalCascadeTracer

    # Load cityA-dataset.parquet
    df = pd.read_parquet('data/cityA-dataset.parquet')
    unique_uids = df['uid'].unique()[:1000]
    df = df[df['uid'].isin(unique_uids)].copy()
    df = df.dropna(subset=['x', 'y', 'd', 't'])

    print(f"Loaded dataset with {df.shape[0]} rows and {df['uid'].nunique()} users.")

    for w in [3, 4, 5]:
        tracer = UniversalCascadeTracer(df)
        print(f"\n--- Running for window size W = {w} ---")
        
        # Let's see the local hubs count and stats
        user_local_hubs, all_local_centroids, event_log_no_global, user_local_labels = tracer.build_local_hubs(w)
        num_local_centroids = len(all_local_centroids)
        print(f"Number of local centroids extracted: {num_local_centroids}")
        
        # Run global clustering
        tracer.build_universal_hubs_and_log(radius_K=2.0, smoothing_window=w)
        print(f"Number of global hubs (R=2.0): {len(tracer.global_hubs)}")

if __name__ == '__main__':
    main()
