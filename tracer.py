import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from sklearn.cluster import HDBSCAN, AgglomerativeClustering
import io
import base64

class UniversalCascadeTracer:
    def __init__(self, raw_df, smoothing_window=5, min_cluster_sizes=[15, 10, 5, 3]):
        # raw_df 包含所有天數的資料
        self.raw_df = raw_df.sort_values(['uid', 'd', 't']).reset_index(drop=True)
        self.smoothing_window = smoothing_window
        self.mcs_list = min_cluster_sizes
        
        self.global_hubs = {} # {g_id: (x, y)}
        self.user_local_hubs = {} # {uid: {l_id: (x, y)}}
        self.event_log = pd.DataFrame()

    def _cluster_logic(self, coords, merge_dist=8.0):
        best_labels = None
        for mcs in self.mcs_list:
            db = HDBSCAN(min_cluster_size=mcs, copy=True).fit(coords)
            unique_zones = set(db.labels_) - {-1}
            best_labels = db.labels_
            if len(unique_zones) > 1: break
                
        temp_df = pd.DataFrame(coords, columns=['x', 'y'])
        temp_df['zone_id'] = best_labels
        
        temp_c = temp_df[temp_df['zone_id'] != -1].groupby('zone_id')[['x', 'y']].mean()
        if len(temp_c) >= 2:
            agg = AgglomerativeClustering(n_clusters=None, distance_threshold=merge_dist, linkage='single')
            mapping = dict(zip(temp_c.index, agg.fit_predict(temp_c)))
            temp_df['zone_id'] = temp_df['zone_id'].map(lambda x: mapping.get(x, -1))
            
        centroids = temp_df[temp_df['zone_id'] != -1].groupby('zone_id')[['x', 'y']].mean().to_dict('index')
        return temp_df['zone_id'].values, centroids

    def build_universal_hubs_and_log(self, radius_K):
        all_local_centroids = []
        hub_events = []
        
        for uid, user_df in self.raw_df.groupby('uid'):
            smooth_x = user_df['x'].rolling(window=self.smoothing_window, center=True, min_periods=1).median()
            smooth_y = user_df['y'].rolling(window=self.smoothing_window, center=True, min_periods=1).median()
            coords = np.column_stack((smooth_x, smooth_y))
            
            labels, centroids = self._cluster_logic(coords)
            
            self.user_local_hubs[uid] = {}
            for l_id, center in centroids.items():
                coord = (center['x'], center['y'])
                self.user_local_hubs[uid][l_id] = coord
                all_local_centroids.append({'uid': uid, 'l_id': l_id, 'x': coord[0], 'y': coord[1]})
            
            user_df_copy = user_df.copy()
            user_df_copy['local_hub'] = labels
            valid_events = user_df_copy[user_df_copy['local_hub'] != -1]
            
            for _, row in valid_events.iterrows():
                hub_events.append({
                    'uid': uid, 'd': row['d'], 't': row['t'],
                    'local_hub': row['local_hub']
                })

        if not all_local_centroids:
            return

        centroid_df = pd.DataFrame(all_local_centroids)
        global_labels, global_centroids = self._cluster_logic(centroid_df[['x', 'y']].values, merge_dist=radius_K)
        centroid_df['global_hub'] = global_labels
        
        self.global_hubs = {g_id: (val['x'], val['y']) for g_id, val in global_centroids.items()}
        
        mapping_dict = centroid_df.set_index(['uid', 'l_id'])['global_hub'].to_dict()
        
        self.event_log = pd.DataFrame(hub_events)
        self.event_log['global_hub'] = self.event_log.apply(
            lambda x: mapping_dict.get((x['uid'], x['local_hub']), -1), axis=1
        )

    def trace_cascade_by_day(self, target_d, target_t_range, target_global_hub):
        day_events = self.event_log[self.event_log['d'] == target_d]
        if day_events.empty:
            return {}, {}
            
        t_start, t_end = target_t_range
        
        primary_hits = day_events[
            (day_events['t'] >= t_start) & 
            (day_events['t'] <= t_end) & 
            (day_events['global_hub'] == target_global_hub)
        ]
        
        # {uid: t_exp}
        p_info_raw = primary_hits.groupby('uid')['t'].min().to_dict()
        primary_uids = set(p_info_raw.keys())
        
        primary_info = {uid: {'t': t, 'hub': target_global_hub} for uid, t in p_info_raw.items()}
        secondary_info = {}
        
        for p_uid, t_exp in p_info_raw.items():
            p_after = day_events[(day_events['uid'] == p_uid) & (day_events['t'] > t_exp)]
            
            for _, row in p_after.iterrows():
                hub_t = row['t']
                p_global_hub = row['global_hub']
                
                if p_global_hub == -1: continue 
                
                sync_events = day_events[
                    (day_events['t'] == hub_t) & 
                    (day_events['global_hub'] == p_global_hub) & 
                    (day_events['uid'] != p_uid)
                ]
                
                for s_uid in sync_events['uid'].unique():
                    if s_uid not in primary_uids:
                        if s_uid not in secondary_info or secondary_info[s_uid]['t'] > hub_t:
                            secondary_info[s_uid] = {'t': hub_t, 'hub': p_global_hub}
                            
        return primary_info, secondary_info

def plot_to_base64(plt):
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return f"data:image/png;base64,{img_str}"

def generate_hubs_plot(tracer):
    plt.figure(figsize=(10, 8))
    
    if not tracer.global_hubs:
        return ""
        
    g_x = [coord[0] for coord in tracer.global_hubs.values()]
    g_y = [coord[1] for coord in tracer.global_hubs.values()]
    g_ids = list(tracer.global_hubs.keys())
    
    # Plot Local Hubs First (Background)
    all_l_x = []
    all_l_y = []
    for user_hubs in tracer.user_local_hubs.values():
        for l_coord in user_hubs.values():
            all_l_x.append(l_coord[0])
            all_l_y.append(l_coord[1])
            
    if all_l_x:
        plt.scatter(all_l_x, all_l_y, c='dodgerblue', marker='s', s=30, alpha=0.3, zorder=2, label='Local Hubs')
    
    # Plot Global Hubs
    plt.scatter(g_x, g_y, c='red', marker='s', s=200, edgecolor='black', zorder=5, label='Global Hubs')
    
    for i, txt in enumerate(g_ids):
        plt.annotate(f"G{txt}", (g_x[i], g_y[i]), xytext=(5, 5), textcoords='offset points', fontsize=9, color='darkred')

    plt.title('All Hubs Topology (Global & Local)', weight='bold', fontsize=14)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    return plot_to_base64(plt)

def generate_impact_plot(tracer, target_d, target_global_hub, primary_info, secondary_info, draw_paths=True, traffic_mode=False, user_trajectory=None):
    plt.figure(figsize=(10, 8))
    
    day_raw = tracer.raw_df[tracer.raw_df['d'] == target_d]
    if not day_raw.empty:
        plt.scatter(day_raw['x'], day_raw['y'], c='lightgray', s=5, alpha=0.1, zorder=1, label='All Coordinates')
    
    if target_global_hub in tracer.global_hubs:
        g_coord = tracer.global_hubs[target_global_hub]
        hub_label = 'Blocked Hub' if traffic_mode else 'Trigger Global Hub'
        plt.scatter(g_coord[0], g_coord[1], c='black', marker='*', s=250, edgecolor='white', zorder=6, label=hub_label)
        
    min_x, max_x = float('inf'), float('-inf')
    min_y, max_y = float('inf'), float('-inf')
    
    # Draw Primary Impact Paths and Hubs
    px, py = [], []
    for uid, info in primary_info.items():
        t_exp = info['t']
        h = info['hub']
        
        # Path drawing
        if draw_paths and not day_raw.empty:
            if traffic_mode:
                window = 1
                user_data = day_raw[(day_raw['uid'] == uid) & (day_raw['t'] >= t_exp - window) & (day_raw['t'] <= t_exp + window)].sort_values('t').copy()
                if not user_data.empty:
                    # Snap the contact point to the global hub coordinate for visual connection
                    if target_global_hub in tracer.global_hubs:
                        g_coord = tracer.global_hubs[target_global_hub]
                        user_data.loc[user_data['t'] == t_exp, 'x'] = g_coord[0]
                        user_data.loc[user_data['t'] == t_exp, 'y'] = g_coord[1]
                        
                    before_contact = user_data[user_data['t'] <= t_exp]
                    after_contact = user_data[user_data['t'] >= t_exp]
                    
                    if not before_contact.empty:
                        plt.plot(before_contact['x'], before_contact['y'], color='dodgerblue', linestyle='-', marker='.', markersize=4, alpha=0.6, zorder=3)
                        min_x = min(min_x, before_contact['x'].min())
                        max_x = max(max_x, before_contact['x'].max())
                        min_y = min(min_y, before_contact['y'].min())
                        max_y = max(max_y, before_contact['y'].max())
                    if not after_contact.empty:
                        plt.plot(after_contact['x'], after_contact['y'], color='red', linestyle='-', marker='.', markersize=4, alpha=0.8, zorder=4)
                        min_x = min(min_x, after_contact['x'].min())
                        max_x = max(max_x, after_contact['x'].max())
                        min_y = min(min_y, after_contact['y'].min())
                        max_y = max(max_y, after_contact['y'].max())
            else:
                user_data = day_raw[(day_raw['uid'] == uid) & (day_raw['t'] >= t_exp)].sort_values('t')
                if not user_data.empty:
                    plt.plot(user_data['x'], user_data['y'], color='red', linestyle='-', marker='.', markersize=4, alpha=0.7, zorder=4)

        if h in tracer.global_hubs:
            px.append(tracer.global_hubs[h][0])
            py.append(tracer.global_hubs[h][1])
            
    if px and not traffic_mode:
        plt.scatter(px, py, c='red', marker='s', s=60, zorder=5, label='Primary Impact Hubs')
        
    # Draw Secondary Impact Paths and Hubs
    sx, sy = [], []
    if not traffic_mode:
        for uid, info in secondary_info.items():
            t_exp = info['t']
            h = info['hub']
            
            # Path drawing
            if draw_paths and not day_raw.empty:
                user_data = day_raw[(day_raw['uid'] == uid) & (day_raw['t'] >= t_exp)].sort_values('t')
                if not user_data.empty:
                    plt.plot(user_data['x'], user_data['y'], color='gold', linestyle='--', marker='.', markersize=4, alpha=0.7, zorder=3)

            if h in tracer.global_hubs:
                sx.append(tracer.global_hubs[h][0])
                sy.append(tracer.global_hubs[h][1])
                
        if sx:
            plt.scatter(sx, sy, c='gold', marker='s', s=60, edgecolor='black', linewidth=0.5, zorder=4, label='Secondary Impact Hubs')

    if user_trajectory:
        ux = [float(p['x']) for p in user_trajectory]
        uy = [float(p['y']) for p in user_trajectory]
        plt.plot(ux, uy, color='blue', linestyle='-', marker='o', markersize=6, linewidth=2, zorder=7)
        plt.scatter(ux, uy, c='cyan', s=100, edgecolor='blue', zorder=8)

    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    
    if draw_paths:
        if traffic_mode:
            before_line = mlines.Line2D([], [], color='dodgerblue', linestyle='-', marker='.', label='Path Before Hub')
            after_line = mlines.Line2D([], [], color='red', linestyle='-', marker='.', label='Path After Hub')
            by_label['Path Before Hub'] = before_line
            by_label['Path After Hub'] = after_line
            if 'Primary Impact Path' in by_label:
                del by_label['Primary Impact Path']
            if 'Secondary Impact Path' in by_label:
                del by_label['Secondary Impact Path']
                
            if min_x != float('inf') and min_x != max_x:
                pad_x = max((max_x - min_x) * 0.1, 5)
                pad_y = max((max_y - min_y) * 0.1, 5)
                plt.xlim(min_x - pad_x, max_x + pad_x)
                plt.ylim(min_y - pad_y, max_y + pad_y)
            elif target_global_hub in tracer.global_hubs:
                g_coord = tracer.global_hubs[target_global_hub]
                plt.xlim(g_coord[0] - 20, g_coord[0] + 20)
                plt.ylim(g_coord[1] - 20, g_coord[1] + 20)
        else:
            primary_line = mlines.Line2D([], [], color='red', linestyle='-', marker='.', label='Primary Impact Path')
            secondary_line = mlines.Line2D([], [], color='gold', linestyle='--', marker='.', label='Secondary Impact Path')
            by_label['Primary Impact Path'] = primary_line
            by_label['Secondary Impact Path'] = secondary_line
        
    if user_trajectory:
        traj_line = mlines.Line2D([], [], color='blue', linestyle='-', marker='o', label='User Trajectory')
        by_label['User Trajectory'] = traj_line

    title_suffix = "(Traffic Blockage Mode)" if traffic_mode else ("(With Paths)" if draw_paths else "(Hubs Only)")
    if user_trajectory:
        title_suffix += " + User Trajectory"
    plt.title(f'Impact Tracing for G{target_global_hub} on Day {target_d} {title_suffix}', weight='bold', fontsize=14)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(by_label.values(), by_label.keys(), loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=3)
    return plot_to_base64(plt)
