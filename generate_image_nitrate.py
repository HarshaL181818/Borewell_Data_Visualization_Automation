# === generate_nitrate_contour.py ===

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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

    # Convert to numeric
    df['Easting'] = pd.to_numeric(df['Easting'], errors='coerce')
    df['Northing'] = pd.to_numeric(df['Northing'], errors='coerce')
    df['Nitrate'] = pd.to_numeric(df['Nitrate'], errors='coerce')

    # Drop missing values
    df = df.dropna(subset=['Easting', 'Northing', 'Nitrate'])

    # Interpolation grid
    grid_x, grid_y = np.mgrid[
        df['Easting'].min():df['Easting'].max():100j,
        df['Northing'].min():df['Northing'].max():100j
    ]

    # Bounds to lat/lon
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
    with open(os.path.join(output_dir, "nitrate_bounds.json"), "w") as f:
        json.dump(bounds_dict, f, indent=2)

    # Interpolate nitrate
    grid_nitrate = griddata(
        points=(df['Easting'], df['Northing']),
        values=df['Nitrate'],
        xi=(grid_x, grid_y),
        method='cubic'
    )

    # Levels
    n_min, n_max = np.nanmin(grid_nitrate), np.nanmax(grid_nitrate)
    n_range = n_max - n_min
    n_interval = 1.0 if n_range > 10 else 0.5 if n_range > 5 else 0.2 if n_range > 2 else 0.1

    nitrate_levels = np.arange(
        np.floor(n_min / n_interval) * n_interval,
        np.ceil(n_max / n_interval) * n_interval + n_interval,
        n_interval
    )

    # Plot nitrate contour
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='none')
    ax.patch.set_alpha(0)
    contourf_nitrate = ax.contourf(grid_x, grid_y, grid_nitrate,
                                   levels=nitrate_levels,
                                   cmap='plasma',
                                   alpha=0.7)

    # Colorbar
    # cbar_nitrate = plt.colorbar(contourf_nitrate, ax=ax, label='Nitrate (mg/L)')
    # cbar_nitrate.set_ticks(nitrate_levels)

    # Scatter points
    ax.scatter(df['Easting'], df['Northing'],
               c=df['Nitrate'],
               cmap='plasma',
               edgecolor='black',
               linewidth=0.7,
               s=50)

    # Bounding box
    bbox_x = df['Easting'].min()
    bbox_y = df['Northing'].min()
    bbox_width = df['Easting'].max() - bbox_x
    bbox_height = df['Northing'].max() - bbox_y
    bbox_rect = Rectangle((bbox_x, bbox_y), bbox_width, bbox_height,
                          linewidth=2, edgecolor='blue', facecolor='none', linestyle='--')
    ax.add_patch(bbox_rect)

    ax.axis('off')
    plt.savefig(os.path.join(output_dir, "groundwater_contour_true_scale.png"),
                dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    print("\nNitrate contour image and bounding box saved.")

if __name__ == "__main__":
    main()
