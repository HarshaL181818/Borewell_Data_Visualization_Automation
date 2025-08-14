# === generate_contour.py ===

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Rectangle
from scipy.interpolate import griddata
import tkinter as tk
from tkinter import filedialog, messagebox
from pyproj import Transformer

def select_file_gui():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if not file_path:
        messagebox.showwarning("No file selected", "Please select an Excel file to proceed.")
        sys.exit(0)
    return file_path

def main():
    file_path = select_file_gui()
    output_dir = "output_files"
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    if 'Name' in df.columns and df['Name'].astype(str).str.contains('TOC1', na=False).any():
        df = df[df['Name'].str.contains('TOC1', na=False)].copy()

    if 'Groundwater Elevation mAHD' in df.columns:
        df = df[df['Groundwater Elevation mAHD'].notna()]
        df = df[df['Groundwater Elevation mAHD'] != '-']

    df['Easting'] = pd.to_numeric(df['Easting'], errors='coerce')
    df['Northing'] = pd.to_numeric(df['Northing'], errors='coerce')
    df['Groundwater Elevation mAHD'] = pd.to_numeric(df['Groundwater Elevation mAHD'], errors='coerce')
    df = df.dropna(subset=['Easting', 'Northing', 'Groundwater Elevation mAHD'])

    # Interpolation grid (in meters)
    grid_x, grid_y = np.mgrid[
        df['Easting'].min():df['Easting'].max():100j,
        df['Northing'].min():df['Northing'].max():100j
    ]

    # Reproject grid corners to get lat/lon bounds
    transformer = Transformer.from_crs("EPSG:32755", "EPSG:4326", always_xy=True)
    min_easting, max_easting = grid_x.min(), grid_x.max()
    min_northing, max_northing = grid_y.min(), grid_y.max()
    min_lon, min_lat = transformer.transform(min_easting, min_northing)
    max_lon, max_lat = transformer.transform(max_easting, max_northing)

    bounds_dict = {
        "min_lat": min_lat,
        "min_lon": min_lon,
        "max_lat": max_lat,
        "max_lon": max_lon
    }
    with open(os.path.join(output_dir, "image_bounds.json"), "w") as f:
        json.dump(bounds_dict, f, indent=2)

    # Interpolation
    grid_z = griddata(
        points=(df['Easting'], df['Northing']),
        values=df['Groundwater Elevation mAHD'],
        xi=(grid_x, grid_y),
        method='cubic'
    )

    dz_dx, dz_dy = np.gradient(grid_z)
    magnitude = np.sqrt(dz_dx**2 + dz_dy**2)
    u = -dz_dx / (magnitude + 1e-10)
    v = -dz_dy / (magnitude + 1e-10)

    z_min, z_max = df['Groundwater Elevation mAHD'].min(), df['Groundwater Elevation mAHD'].max()
    z_range = z_max - z_min
    interval = 1.0 if z_range > 10 else 0.5 if z_range > 5 else 0.2 if z_range > 2 else 0.1 if z_range > 1 else 0.05 if z_range > 0.5 else 0.01

    contour_levels = np.arange(
        np.floor(z_min / interval) * interval,
        np.ceil(z_max / interval) * interval + interval,
        interval
    )

    fig, ax = plt.subplots(figsize=(12, 8), facecolor='none')
    ax.patch.set_alpha(0)
    ax.contourf(grid_x, grid_y, grid_z, levels=contour_levels, cmap='viridis', alpha=0.6)
    ax.scatter(df['Easting'], df['Northing'], color='black', edgecolor='black', linewidth=0.8, s=40)
    step = 10
    ax.quiver(grid_x[::step, ::step], grid_y[::step, ::step], u[::step, ::step], v[::step, ::step], color='red', scale=25, width=0.002)

    # Bounding box rectangle
    bbox_x = df['Easting'].min()
    bbox_y = df['Northing'].min()
    bbox_width = df['Easting'].max() - bbox_x
    bbox_height = df['Northing'].max() - bbox_y
    bbox_rect = Rectangle((bbox_x, bbox_y), bbox_width, bbox_height, linewidth=2, edgecolor='blue', facecolor='none', linestyle='--')
    ax.add_patch(bbox_rect)

    ax.axis('off')
    plt.savefig(os.path.join(output_dir, "groundwater_contour_true_scale.png"), dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    print("\n Contour image and bounding box saved.")

if __name__ == "__main__":
    main()

