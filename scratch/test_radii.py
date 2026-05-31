import pandas as pd
import numpy as np
import os
import sys

def main():
    sys.path.append(os.path.abspath('.'))
    from module import UniversalCascadeTracer

    df = pd.read_parquet('data/cityA-dataset.parquet')
    unique_uids = df['uid'].unique()[:1000]
    df = df[df['uid'].isin(unique_uids)].copy()
    df = df.dropna(subset=['x', 'y', 'd', 't'])

    tracer = UniversalCascadeTracer(df)
    # Build local hubs with W=3
    tracer.build_local_hubs(smoothing_window=3)

    for r in [1.0, 2.0, 3.0, 5.0, 8.0, 15.0]:
        tracer.build_universal_hubs_and_log(radius_K=r, smoothing_window=3)
        print(f"Radius R = {r} -> Number of global hubs: {len(tracer.global_hubs)}")

if __name__ == '__main__':
    main()
