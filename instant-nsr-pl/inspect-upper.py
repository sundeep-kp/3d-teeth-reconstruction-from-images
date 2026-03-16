
import pickle
import numpy as np

with open('../meta_info/upper.pkl', 'rb') as f:
    poses = pickle.load(f)

print("Number of poses:", len(poses))

for i, p in enumerate(poses):
    print(f"\nPose {i}")
    print(np.array(p))

