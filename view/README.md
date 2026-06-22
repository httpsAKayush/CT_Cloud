# Visualize one patient's union cloud
python view/visualize.py -p s1388 --source union

# Visualize one patient's raw/full-body cloud
python view/visualize.py -p s1388 --source raw

# Visualize both union and raw cloud for one patient
python view/visualize.py -p s1388 --source both


# Visualize multiple patients (union)
python view/visualize.py -p s1388 s1371 s1369 --source union

# Visualize multiple patients (raw)
python view/visualize.py -p s1388 s1371 s1369 --source raw

# Visualize multiple patients (both)
python view/visualize.py -p s1388 s1371 s1369 --source both


# Visualize all union clouds
python view/visualize.py --all --source union

# Visualize all raw clouds
python view/visualize.py --all --source raw

# Visualize all union + raw clouds
python view/visualize.py --all --source both


# Save all union cloud views to output/union/
python view/visualize.py --all --source union --save

# Save all raw cloud views to output/raw/
python view/visualize.py --all --source raw --save

# Save all union + raw cloud views
python view/visualize.py --all --source both --save


# Save to custom directory
python view/visualize.py --all --source both --save --save-dir ~/Desktop/views


# Visualize a custom .ply file
python view/visualize.py --ply /path/to/file.ply

# Visualize multiple custom .ply files
python view/visualize.py --ply file1.ply file2.ply file3.ply

# Visualize all .ply files in a folder
python view/visualize.py --dir /path/to/ply_folder


# Generate point cloud directly from segmentation folder and visualize
python view/visualize.py --seg /path/to/s1388

# Generate from segmentation folder and save views
python view/visualize.py --seg /path/to/s1388 --save