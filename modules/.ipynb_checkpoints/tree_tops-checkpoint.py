
import numpy as np
import rasterio
from scipy.ndimage import maximum_filter, label
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

def detect_tree_tops(ndsm_file, neighborhood_size=50, min_height_threshold=10, sigma=2):
    """
    Detect tree tops from an nDSM raster.

    Parameters:
    ndsm_file (str): Path to the nDSM raster file.
    neighborhood_size (int): Size of the neighborhood for local maxima detection (in pixels).
    min_height_threshold (float): Minimum height of trees to be detected (in meters).
    sigma (float): Gaussian smoothing parameter to reduce noise in the nDSM.

    Returns:
    None: Displays the nDSM with detected tree tops plotted as scatter points.
    """
    # Load the nDSM raster
    with rasterio.open(ndsm_file) as src:
        ndsm = src.read(1)  # Read the nDSM data
        transform = src.transform

    # Apply Gaussian filter to smooth the nDSM and reduce noise
    smoothed_ndsm = gaussian_filter(ndsm, sigma=sigma)

    # Apply a maximum filter to detect local maxima (tree tops)
    local_max = maximum_filter(smoothed_ndsm, size=neighborhood_size) == smoothed_ndsm

    # Apply a height threshold to only keep tree tops taller than the given height threshold
    tree_tops_mask = local_max & (smoothed_ndsm > min_height_threshold)

    # Label each detected tree top (connected components)
    labeled_treetops, num_features = label(tree_tops_mask)

    # Extract the coordinates of the detected tree tops
    tree_top_coords = np.column_stack(np.where(labeled_treetops > 0))

    # Mask negative values from the nDSM (anything below 0)
    masked_ndsm = np.ma.masked_where(smoothed_ndsm < 0, smoothed_ndsm)

    # Dynamically set vmax to the maximum value in the nDSM
    vmax_value = np.max(smoothed_ndsm)

    # Create a custom grayscale colormap where masked values (negative) are black
    cmap = plt.cm.gray
    cmap.set_bad(color='black')  # Set masked values (below 0) to black

    # Plot the nDSM and detected tree tops
    plt.figure(figsize=(10, 10))

    # Plot the nDSM in black and white, with masked negative values shown in black
    img = plt.imshow(masked_ndsm, cmap=cmap, vmin=0, vmax=vmax_value, alpha=0.8)

    # Overlay detected tree tops as scatter points
    if len(tree_top_coords) > 0:
        plt.scatter(tree_top_coords[:, 1], tree_top_coords[:, 0], color='red', marker='o', s=5, label='Tree Tops')

    # Add a grayscale colorbar
    cbar = plt.colorbar(img)  # Apply the grayscale colormap to the colorbar
    cbar.set_label('Elevation (m)')
    cbar.ax.yaxis.set_tick_params(color='black')  # Set the color of the tick labels to black
    cbar.outline.set_edgecolor('black')  # Make the colorbar outline black

    plt.title(f'Detected Tree Tops taller than {min_height_threshold} meters: {num_features}')
    plt.legend()
    plt.show()
