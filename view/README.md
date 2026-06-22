cd ~/ct_pipeline

# View one patient (interactive)
python view/visualize.py -p s1388

# View multiple
python view/visualize.py -p s1388 s1371 s1369

# View all
python view/visualize.py --all

# Save all to view/output/
python view/visualize.py --all --save

# Save to custom folder
python view/visualize.py -p s1388 --save --save-dir ~/Desktop/views

# Point at a custom .ply file directly
python view/visualize.py --ply /path/to/file.ply

# Just print stats, no plot
python view/visualize.py --all --no-plot 2>/dev/null

# Point at patient folder (auto-finds segmentations/ inside)
python view/visualize.py --seg ~/Downloads/Totalsegmentator_dataset_small_v201/wholebody/s1388

# Point at segmentations folder directly
python view/visualize.py --seg ~/Downloads/Totalsegmentator_dataset_small_v201/wholebody/s1388/segmentations

# Multiple patients via folder
python view/visualize.py --seg ~/Downloads/.../s1388 ~/Downloads/.../s1371

# Mix --seg and --p together
python view/visualize.py --seg ~/Downloads/.../s1388 -p s1371 --save