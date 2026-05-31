import pandas as pd
import os
import sys

# Add the parent directory to sys.path so we can import module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from module import UniversalCascadeTracer

def main():
    # Load dataset
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cityA-dataset.parquet')
    file_path = os.path.abspath(data_path)
    print("Loading data from:", file_path)
    
    uids_df = pd.read_parquet(file_path, columns=['uid'])
    unique_uids = sorted(uids_df['uid'].unique())
    selected_uids = unique_uids[:1000]
    
    select_df = pd.read_parquet(file_path, filters=[('uid', 'in', selected_uids)])
    select_df = select_df.dropna(subset=['x', 'y', 'd', 't'])
    
    print("Building tracer...")
    tracer = UniversalCascadeTracer(select_df)
    tracer.build_universal_hubs_and_log(radius_K=1.0)
    
    print("Total global hubs:", len(tracer.global_hubs))
    for h_id, coord in tracer.global_hubs.items():
        print(f"G{h_id}: {coord}")
        
    print("\nTracing day 1, hub G2...")
    primary_info, secondary_info = tracer.trace_cascade_by_day(1, (1, 48), 2)
    
    print("Primary info size:", len(primary_info))
    print("Secondary info size:", len(secondary_info))
    
    print("\nSecondary info details:")
    for uid, info in list(secondary_info.items())[:10]:
        print(f"uid: {uid}, info: {info}")
        
    # Check infection times
    hub_infection_times = {}
    hub_infection_levels = {}
    hub_infection_sources = {}
    
    event_hubs = [2]
    event_day = 1
    
    hub_infection_times[2] = 1
    hub_infection_levels[2] = '出事源頭 (Global Hub)'
    hub_infection_sources[2] = 2
    
    for uid, info in primary_info.items():
        h = info['hub']
        t = info['t']
        if h not in hub_infection_times or t < hub_infection_times[h]:
            hub_infection_times[h] = t
            hub_infection_levels[h] = '直接影響 (Primary)'
            hub_infection_sources[h] = 2
            
    for uid, info in secondary_info.items():
        h = info['hub']
        t = info['t']
        if h not in hub_infection_times or t < hub_infection_times[h]:
            hub_infection_times[h] = t
            if h not in hub_infection_levels:
                hub_infection_levels[h] = '間接影響 (Secondary)'
                hub_infection_sources[h] = 2
                
    print("\nHub infection times:")
    for h, t in sorted(hub_infection_times.items()):
        coord = tracer.global_hubs.get(h, None)
        print(f"Hub G{h} at {coord}: time={t}, level={hub_infection_levels[h]}")

if __name__ == '__main__':
    main()
