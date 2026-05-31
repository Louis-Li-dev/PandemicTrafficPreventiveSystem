from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import os
import glob
from module import UniversalCascadeTracer, generate_hubs_plot, generate_impact_plot

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')


tracer_instance = None
df_cache = None

def get_data():
    global df_cache
    if df_cache is None:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'cityA-dataset.parquet')
        df_cache = pd.read_parquet(data_path).rename({
            'x_full': 'x',
            'y_full': 'y'
        })
        print(df_cache.columns)
    return df_cache

@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    files = glob.glob('data/*.parquet')
    datasets = [os.path.basename(f) for f in files]
    return jsonify({'status': 'success', 'datasets': datasets})

@app.route('/api/build_hubs', methods=['POST'])
def build_hubs():
    global tracer_instance
    data = request.json
    num_users = data.get('numUsers', 1000)
    radius_K = data.get('radiusK', 1.0)
    dataset_name = data.get('dataset', 'cityA-dataset.parquet')
    
    file_path = os.path.join(os.path.dirname(__file__), 'data', dataset_name)
    
    # Optimize loading: read only 'uid' column first, then read selected UIDs to avoid ArrowMemoryError
    uids_df = pd.read_parquet(file_path, columns=['uid'])
    unique_uids = sorted(uids_df['uid'].unique())
    selected_uids = unique_uids[:num_users]
    
    select_df = pd.read_parquet(file_path, filters=[('uid', 'in', selected_uids)])
    select_df = select_df.dropna(subset=['x', 'y', 'd', 't'])
    
    tracer_instance = UniversalCascadeTracer(select_df)
    tracer_instance.build_universal_hubs_and_log(radius_K=radius_K)
    
    plot_b64 = generate_hubs_plot(tracer_instance)
    
    local_hubs_count = sum(len(hubs) for hubs in tracer_instance.user_local_hubs.values())
    
    return jsonify({
        'status': 'success',
        'global_hubs_count': len(tracer_instance.global_hubs),
        'local_hubs_count': local_hubs_count,
        'hubs_plot': plot_b64
    })

@app.route('/api/get_options', methods=['GET'])
def get_options():
    global tracer_instance
    if not tracer_instance:
        return jsonify({'error': 'Hubs not built yet'}), 400
        
    days = sorted([int(x) for x in tracer_instance.event_log['d'].unique().tolist()])
    hubs = sorted([int(x) for x in list(tracer_instance.global_hubs.keys())])
    
    return jsonify({
        'days': days,
        'hubs': hubs
    })

@app.route('/api/trace_cascade', methods=['POST'])
def trace_cascade():
    global tracer_instance
    if not tracer_instance:
        return jsonify({'error': 'Hubs not built yet'}), 400
        
    data = request.json
    target_d = data.get('day')
    t_start = data.get('tStart')
    t_end = data.get('tEnd')
    target_global_hub = data.get('hub')
    is_traffic_tab = data.get('isTrafficTab', False)
    
    primary_info, secondary_info = tracer_instance.trace_cascade_by_day(
        target_d, (t_start, t_end), target_global_hub
    )
        
    plot_b64_paths = generate_impact_plot(tracer_instance, target_d, target_global_hub, primary_info, secondary_info if not is_traffic_tab else {}, draw_paths=True, traffic_mode=is_traffic_tab)
    plot_b64_hubs = generate_impact_plot(tracer_instance, target_d, target_global_hub, primary_info, secondary_info if not is_traffic_tab else {}, draw_paths=False, traffic_mode=is_traffic_tab)
    
    def format_time(t):
        hours = int(t * 30 // 60)
        mins = int((t * 30) % 60)
        return f"{hours:02d}:{mins:02d}"

    primary_table = []
    for uid, info in primary_info.items():
        primary_table.append({
            'uid': int(uid),
            'hub': int(info['hub']),
            'time': format_time(info['t'])
        })
        
    secondary_table = []
    for uid, info in secondary_info.items():
        secondary_table.append({
            'uid': int(uid),
            'hub': int(info['hub']),
            'time': format_time(info['t'])
        })
        
    return jsonify({
        'status': 'success',
        'primary_users': primary_table,
        'secondary_users': secondary_table,
        'impact_plot_paths': plot_b64_paths,
        'impact_plot_hubs': plot_b64_hubs
    })

@app.route('/api/check_warning', methods=['POST'])
def check_warning():
    global tracer_instance
    if not tracer_instance:
        return jsonify({'error': 'Hubs not built yet'}), 400
        
    data = request.json
    trajectory = data.get('trajectory', [])
    event_day = int(data.get('eventDay', 1))
    
    event_hubs = data.get('eventHubs', [])
    if not event_hubs:
        event_hubs = [int(data.get('eventHub', 0))]
    else:
        event_hubs = [int(h) for h in event_hubs]
        
    warnings = []
    
    hub_infection_times = {}
    hub_infection_levels = {}
    hub_infection_sources = {}
    
    all_primary_info = {}
    all_secondary_info = {}
    
    for event_hub in event_hubs:
        primary_info, secondary_info = tracer_instance.trace_cascade_by_day(
            event_day, (1, 48), event_hub
        )
        
        hub_infection_times[event_hub] = 1
        hub_infection_levels[event_hub] = '出事源頭 (Global Hub)'
        hub_infection_sources[event_hub] = event_hub
        
        all_primary_info.update(primary_info)
        all_secondary_info.update(secondary_info)
        
        for uid, info in primary_info.items():
            h = info['hub']
            t = info['t']
            if h not in hub_infection_times or t < hub_infection_times[h]:
                hub_infection_times[h] = t
                hub_infection_levels[h] = '直接影響 (Primary)'
                hub_infection_sources[h] = event_hub
                
        for uid, info in secondary_info.items():
            h = info['hub']
            t = info['t']
            if h not in hub_infection_times or t < hub_infection_times[h]:
                hub_infection_times[h] = t
                if h not in hub_infection_levels:
                    hub_infection_levels[h] = '間接影響 (Secondary)'
                    hub_infection_sources[h] = event_hub
                    
    def format_time(t_val):
        h = int(t_val * 30 // 60)
        m = int(t_val * 30 % 60)
        return f"{h:02d}:{m:02d}"
        
    overall_min_dist = float('inf')
    
    for point in trajectory:
        t = int(point['time'])
        x = float(point['x'])
        y = float(point['y'])
        
        nearest_event_hub = -1
        min_dist_to_event = float('inf')
        for eh in event_hubs:
            if eh in tracer_instance.global_hubs:
                g_coord = tracer_instance.global_hubs[eh]
                dist = ((g_coord[0] - x)**2 + (g_coord[1] - y)**2)**0.5
                if dist < min_dist_to_event:
                    min_dist_to_event = dist
                    nearest_event_hub = eh
                    
        if min_dist_to_event < overall_min_dist:
            overall_min_dist = min_dist_to_event
            
        nearest_infected_hub = -1
        min_infected_dist = float('inf')
        for g_id, g_coord in tracer_instance.global_hubs.items():
            if g_id in hub_infection_times:
                dist = ((g_coord[0] - x)**2 + (g_coord[1] - y)**2)**0.5
                if dist < min_infected_dist:
                    min_infected_dist = dist
                    nearest_infected_hub = g_id
                
        if min_infected_dist < 10.0:
            level = hub_infection_levels[nearest_infected_hub]
            inf_time = hub_infection_times[nearest_infected_hub]
            source_hub = hub_infection_sources[nearest_infected_hub]
            warnings.append({
                'time': format_time(t),
                'x': x,
                'y': y,
                'hub': f"G{nearest_infected_hub}",
                'level': level,
                'message': f"注意！時間 {format_time(t)} 進入 {level} Hub G{nearest_infected_hub} (從 {format_time(inf_time)} 起受 G{source_hub} 事故影響)。距事發源頭 G{nearest_event_hub} 距離: {round(min_dist_to_event, 2)}"
            })
                
    primary_users = [{'uid': int(uid), 'hub': int(info['hub']), 'time': format_time(info['t'])} for uid, info in all_primary_info.items()]
    secondary_users = [{'uid': int(uid), 'hub': int(info['hub']), 'time': format_time(info['t'])} for uid, info in all_secondary_info.items()]
    
    plot_b64 = generate_impact_plot(
        tracer_instance, event_day, event_hubs[0] if event_hubs else 0, 
        all_primary_info, all_secondary_info, 
        draw_paths=False, user_trajectory=trajectory
    )
            
    return jsonify({
        'status': 'success',
        'overall_min_dist': round(overall_min_dist, 2) if overall_min_dist != float('inf') else None,
        'warnings': warnings,
        'warning_plot': plot_b64,
        'primary_users': primary_users,
        'secondary_users': secondary_users
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True, use_reloader=False)
