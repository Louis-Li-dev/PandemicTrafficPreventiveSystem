from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import os
from tracer import UniversalCascadeTracer, generate_hubs_plot, generate_impact_plot

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
        df_cache = pd.read_parquet(data_path)
    return df_cache

@app.route('/api/build_hubs', methods=['POST'])
def build_hubs():
    global tracer_instance
    data = request.json
    num_users = data.get('numUsers', 1000)
    radius_K = data.get('radiusK', 1.0)
    
    df = get_data()
    select_df = df[df['uid'].isin(range(num_users))].copy()
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
    event_hub = int(data.get('eventHub', 0))
    
    warnings = []
    
    primary_info, secondary_info = tracer_instance.trace_cascade_by_day(
        event_day, (1, 48), event_hub
    )
    
    hub_infection_times = {}
    hub_infection_levels = {}
    
    for uid, info in primary_info.items():
        h = info['hub']
        t = info['t']
        if h not in hub_infection_times or t < hub_infection_times[h]:
            hub_infection_times[h] = t
            hub_infection_levels[h] = '直接影響 (第一層)'
            
    for uid, info in secondary_info.items():
        h = info['hub']
        t = info['t']
        if h not in hub_infection_times or t < hub_infection_times[h]:
            hub_infection_times[h] = t
            if h not in hub_infection_levels:
                hub_infection_levels[h] = '間接影響 (第二層)'
                
    hub_infection_times[event_hub] = 1
    hub_infection_levels[event_hub] = '直接影響 (觸發源)'
    
    for point in trajectory:
        d = int(point.get('d', event_day))
        t = int(point['time'])
        x = float(point['x'])
        y = float(point['y'])
        
        if d != event_day:
            continue
            
        nearest_hub = -1
        min_dist = float('inf')
        for g_id, g_coord in tracer_instance.global_hubs.items():
            dist = ((g_coord[0] - x)**2 + (g_coord[1] - y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                nearest_hub = g_id
                
        if min_dist < 10.0:
            if nearest_hub in hub_infection_times and t >= hub_infection_times[nearest_hub]:
                level = hub_infection_levels[nearest_hub]
                warnings.append({
                    'd': d,
                    'time': t,
                    'x': x,
                    'y': y,
                    'hub': nearest_hub,
                    'distance': round(min_dist, 2),
                    'level': level,
                    'message': f'第 {d} 天 時間 t={t} 進入受影響區域 G{nearest_hub} ({level})'
                })
                
    plot_b64 = generate_impact_plot(
        tracer_instance, event_day, event_hub, 
        primary_info, secondary_info, 
        draw_paths=False, user_trajectory=[p for p in trajectory if int(p.get('d', event_day)) == event_day]
    )
            
    return jsonify({
        'status': 'success',
        'warnings': warnings,
        'warning_plot': plot_b64
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True, use_reloader=False)
