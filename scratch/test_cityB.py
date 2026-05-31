import pandas as pd
import numpy as np
import os
import sys

def main():
    sys.path.append(os.path.abspath('.'))
    from module import UniversalCascadeTracer, evaluate_clustering_quality

    df = pd.read_parquet('data/cityB-dataset.parquet')
    unique_uids = df['uid'].unique()[:1000]
    df = df[df['uid'].isin(unique_uids)].copy()
    df = df.dropna(subset=['x', 'y', 'd', 't'])

    tracer = UniversalCascadeTracer(df)

    for w in [3, 5, 7]:
        tracer.build_universal_hubs_and_log(radius_K=1.0, smoothing_window=w)
        metrics = evaluate_clustering_quality(tracer, df)
        print(f"W={w}: Global Hubs={metrics['Num_Global_Hubs']}, Local Hubs={metrics['Num_Local_Hubs']}, Coverage={metrics['Coverage_pct']:.3f}%, Mean Dist={metrics['Mean_Dist_m']:.3f}m")

if __name__ == '__main__':
    main()
