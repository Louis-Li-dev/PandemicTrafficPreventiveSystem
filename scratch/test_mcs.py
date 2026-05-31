import pandas as pd
import numpy as np
import os
import sys
from sklearn.cluster import HDBSCAN, AgglomerativeClustering

def main():
    sys.path.append(os.path.abspath('.'))
    from module import UniversalCascadeTracer

    df = pd.read_parquet('data/cityA-dataset.parquet')
    unique_uids = df['uid'].unique()[:1000]
    df = df[df['uid'].isin(unique_uids)].copy()
    df = df.dropna(subset=['x', 'y', 'd', 't'])

    mcs_list = [15, 10, 5, 3]

    for w in [3, 4, 5]:
        tracer = UniversalCascadeTracer(df)
        user_local_hubs, all_local_centroids, event_log_no_global, user_local_labels = tracer.build_local_hubs(w)
        coords = np.array([[c['x'], c['y']] for c in all_local_centroids])
        
        print(f"\n--- Analysis for W = {w} (coords count: {len(coords)}) ---")
        
        for mcs in mcs_list:
            db = HDBSCAN(min_cluster_size=mcs, copy=True).fit(coords)
            unique_zones = set(db.labels_) - {-1}
            num_zones = len(unique_zones)
            num_noise = np.sum(db.labels_ == -1)
            print(f"  MCS = {mcs}: found {num_zones} clusters, noise points = {num_noise}")
            if num_zones > 1:
                print(f"  -> Selected MCS: {mcs} (found {num_zones} clusters before merging)")
                
                # Apply merging logic
                temp_df = pd.DataFrame(coords, columns=['x', 'y'])
                temp_df['zone_id'] = db.labels_
                temp_c = temp_df[temp_df['zone_id'] != -1].groupby('zone_id')[['x', 'y']].mean()
                if len(temp_c) >= 2:
                    agg = AgglomerativeClustering(n_clusters=None, distance_threshold=2.0, linkage='single')
                    mapping = dict(zip(temp_c.index, agg.fit_predict(temp_c)))
                    temp_df['zone_id'] = temp_df['zone_id'].map(lambda x: mapping.get(x, -1))
                
                final_zones = set(temp_df['zone_id'].unique()) - {-1}
                print(f"  -> After merging with R=2.0: {len(final_zones)} global hubs")
                break

if __name__ == '__main__':
    main()
