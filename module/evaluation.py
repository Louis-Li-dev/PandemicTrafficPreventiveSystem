import numpy as np

def evaluate_clustering_quality(tracer, raw_df):
    """
    Computes metrics evaluating quality of spatiotemporal clustering:
    - Coverage: % of raw coordinate points classified to a local hub (excluding missing values).
    - Mean Distance: average Euclidean distance between raw coordinates and their classified local hub center.
    """
    total_points = 0
    classified_points = 0
    distances = []
    
    for uid, user_df in raw_df.groupby('uid'):
        xs = user_df['x'].values
        ys = user_df['y'].values
        
        labels = tracer.user_local_labels.get(uid, [])
        if len(labels) != len(user_df):
            continue
            
        user_hubs = tracer.user_local_hubs.get(uid, {})
        for i in range(len(user_df)):
            x_val = xs[i]
            y_val = ys[i]
            if np.isnan(x_val) or np.isnan(y_val):
                continue
                
            total_points += 1
            lbl = labels[i]
            if lbl != -1:
                classified_points += 1
                if lbl in user_hubs:
                    hx, hy = user_hubs[lbl]
                    dist = ((x_val - hx)**2 + (y_val - hy)**2)**0.5
                    distances.append(dist)
                    
    coverage = (classified_points / total_points) * 100.0 if total_points > 0 else 0.0
    mean_dist = np.mean(distances) if distances else 0.0
    
    return {
        'Coverage_pct': coverage,
        'Mean_Dist_m': mean_dist,
        'Num_Global_Hubs': len(tracer.global_hubs),
        'Num_Local_Hubs': sum(len(hubs) for hubs in tracer.user_local_hubs.values())
    }
