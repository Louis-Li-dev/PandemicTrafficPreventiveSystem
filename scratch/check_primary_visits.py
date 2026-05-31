import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module import UniversalCascadeTracer

def main():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cityA-dataset.parquet')
    file_path = os.path.abspath(data_path)
    
    # Load dataset
    uids_df = pd.read_parquet(file_path, columns=['uid'])
    unique_uids = sorted(uids_df['uid'].unique())
    selected_uids = unique_uids[:1000]
    
    select_df = pd.read_parquet(file_path, filters=[('uid', 'in', selected_uids)])
    select_df = select_df.dropna(subset=['x', 'y', 'd', 't'])
    
    tracer = UniversalCascadeTracer(select_df)
    tracer.build_universal_hubs_and_log(radius_K=1.0)
    
    event_day = 1
    event_hub = 6
    
    day_events = tracer.event_log[tracer.event_log['d'] == event_day]
    primary_info, secondary_info = tracer.trace_cascade_by_day(event_day, (1, 48), event_hub)
    
    print("Primary users and their infection times:")
    for uid, info in list(primary_info.items()):
        print(f"  uid: {uid}, infected at G6, time={info['t']}")
        
    print("\nVisits by primary users to G0 after their infection:")
    for uid, info in primary_info.items():
        t_exp = info['t']
        user_visits = day_events[(day_events['uid'] == uid) & (day_events['t'] > t_exp) & (day_events['global_hub'] == 0)]
        for _, row in user_visits.iterrows():
            print(f"  uid {uid} visited G0 at time {row['t']}")
            
if __name__ == '__main__':
    main()
