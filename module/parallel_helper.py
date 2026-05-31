import pandas as pd
import numpy as np
from sklearn.cluster import HDBSCAN, AgglomerativeClustering

def process_single_user(args):
    """
    Processes a single user's trajectory: rolling median smoothing, 
    adaptive HDBSCAN clustering, and Agglomerative clustering to extract local hubs.
    """
    uid, user_df, smoothing_window, mcs_list = args
    
    # 1. Coordinate smoothing
    smooth_x = user_df['x'].rolling(window=smoothing_window, center=True, min_periods=1).median()
    smooth_y = user_df['y'].rolling(window=smoothing_window, center=True, min_periods=1).median()
    coords = np.column_stack((smooth_x, smooth_y))
    
    # 2. Adaptive HDBSCAN clustering
    best_labels = None
    for mcs in mcs_list:
        db = HDBSCAN(min_cluster_size=mcs, copy=True).fit(coords)
        unique_zones = set(db.labels_) - {-1}
        best_labels = db.labels_
        if len(unique_zones) > 1:
            break
            
    temp_df = pd.DataFrame(coords, columns=['x', 'y'])
    temp_df['zone_id'] = best_labels
    
    # 3. Merge close centroids using Agglomerative Clustering
    temp_c = temp_df[temp_df['zone_id'] != -1].groupby('zone_id')[['x', 'y']].mean()
    if len(temp_c) >= 2:
        agg = AgglomerativeClustering(n_clusters=None, distance_threshold=8.0, linkage='single')
        mapping = dict(zip(temp_c.index, agg.fit_predict(temp_c)))
        temp_df['zone_id'] = temp_df['zone_id'].map(lambda x: mapping.get(x, -1))
        
    centroids = temp_df[temp_df['zone_id'] != -1].groupby('zone_id')[['x', 'y']].mean().to_dict('index')
    
    user_local_hubs = {}
    all_local_centroids = []
    for l_id, center in centroids.items():
        coord = (center['x'], center['y'])
        user_local_hubs[l_id] = coord
        all_local_centroids.append({'uid': uid, 'l_id': l_id, 'x': coord[0], 'y': coord[1]})
        
    user_df_copy = user_df.copy()
    user_df_copy['local_hub'] = temp_df['zone_id'].values
    valid_events = user_df_copy[user_df_copy['local_hub'] != -1]
    
    hub_events = []
    for _, row in valid_events.iterrows():
        hub_events.append({
            'uid': uid, 'd': int(row['d']), 't': int(row['t']),
            'local_hub': int(row['local_hub'])
        })
        
    return uid, user_local_hubs, all_local_centroids, hub_events, temp_df['zone_id'].values.tolist()
