import numpy as np
import rasterio
from scipy.ndimage import maximum_filter, label
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from rasterio.plot import show
import pyodbc


# function to calculate the nDSM (DSM - DTM)
def calculate_ndsm(dsm_path, dtm_path, output_ndsm_path):
    """
    Calculate the normalized Digital Surface Model (nDSM) by subtracting DTM from DSM.

    Parameters:
        dsm_path (str): Path to the DSM raster file (Digital Surface Model).
        dtm_path (str): Path to the DTM raster file (Digital Terrain Model).
        output_ndsm_path (str): Path to save the resulting nDSM raster file.
    """
    # Open DSM and DTM raster files
    with rasterio.open(dsm_path) as dsm_dataset, rasterio.open(dtm_path) as dtm_dataset:
        
        # Check that DSM and DTM have the same shape and CRS (Coordinate Reference System)
        if dsm_dataset.shape != dtm_dataset.shape:
            raise ValueError("DSM and DTM must have the same shape.")
        if dsm_dataset.crs != dtm_dataset.crs:
            raise ValueError("DSM and DTM must have the same CRS.")
        
        # Read the raster data as arrays
        dsm_data = dsm_dataset.read(1)  # Reading the first band of DSM
        dtm_data = dtm_dataset.read(1)  # Reading the first band of DTM

        # Handle nodata values by masking them
        dsm_nodata = dsm_dataset.nodata
        dtm_nodata = dtm_dataset.nodata
        
        # Mask nodata values
        if dsm_nodata is not None:
            dsm_data = np.ma.masked_equal(dsm_data, dsm_nodata)
        if dtm_nodata is not None:
            dtm_data = np.ma.masked_equal(dtm_data, dtm_nodata)
        
        # Debugging: Print min/max of DSM and DTM before subtraction
        print(f"DSM Min: {np.min(dsm_data)}, Max: {np.max(dsm_data)}")
        print(f"DTM Min: {np.min(dtm_data)}, Max: {np.max(dtm_data)}")

        # Calculate the nDSM (handle masked arrays to avoid subtracting nodata values)
        ndsm_data = dsm_data - dtm_data

        # Debugging: Print min/max of the nDSM
        print(f"nDSM Min: {np.min(ndsm_data)}, Max: {np.max(ndsm_data)}")

        # Update the metadata from DSM for the output nDSM
        ndsm_meta = dsm_dataset.meta.copy()
        ndsm_meta.update({
            "dtype": "float32",  # Set output to float32 to handle negative values if necessary
            "compress": "lzw"    # Compression option (optional)
        })
        
        # Save the nDSM result to a new raster file
        with rasterio.open(output_ndsm_path, 'w', **ndsm_meta) as ndsm_dataset:
            ndsm_dataset.write(ndsm_data.filled(np.nan).astype(np.float32), 1)
    
    print(f"nDSM has been saved to {output_ndsm_path}")

def local_to_utm(tree_top_coords, transform):
    """
    Convert local tree top coordinates (pixel space) to UTM32N coordinates.

    Parameters:
    - tree_top_coords: List of tuples containing local tree top coordinates (row, col).
    - transform: The affine transformation matrix from the rasterio dataset.
    
    Returns:
    - List of tuples with UTM32N coordinates (x, y).
    """
    utm_coords = []
    
    for row, col in tree_top_coords:
        # Apply the affine transformation to convert local (row, col) to UTM (x, y)
        x_utm, y_utm = transform * (col, row)  # Note: col corresponds to x, row to y
        utm_coords.append((x_utm, y_utm))
    
    return utm_coords


def detect_tree_tops(ndsm_file, neighborhood_size=50, min_height_threshold=10, sigma=2):
    """
    Detect tree tops from an nDSM raster and convert coordinates to UTM32N.

    Parameters:
    ndsm_file (str): Path to the nDSM raster file.
    neighborhood_size (int): Size of the neighborhood for local maxima detection (in pixels).
    min_height_threshold (float): Minimum height of trees to be detected (in meters).
    sigma (float): Gaussian smoothing parameter to reduce noise in the nDSM.

    Displays the nDSM with detected tree tops plotted as scatter points.
    
    Returns:
    - List of UTM32N coordinates of detected tree tops and their heights.
    - matplotlib Figure and Axes objects for saving or further customization.
    """
    # Load the nDSM raster
    with rasterio.open(ndsm_file) as src:
        ndsm = src.read(1)  # Read the nDSM data
        transform = src.transform  # Affine transformation to convert pixel coords to UTM32N

    # Apply Gaussian filter to smooth the nDSM and reduce noise
    smoothed_ndsm = gaussian_filter(ndsm, sigma=sigma)

    # Apply a maximum filter to detect local maxima (tree tops)
    local_max = maximum_filter(smoothed_ndsm, size=neighborhood_size) == smoothed_ndsm

    # Apply a height threshold to only keep tree tops taller than the given height threshold
    tree_tops_mask = local_max & (smoothed_ndsm > min_height_threshold)

    # Label each detected tree top (connected components)
    labeled_treetops, num_features = label(tree_tops_mask)

    # Extract the coordinates of the detected tree tops (local row, col)
    tree_top_coords = np.column_stack(np.where(labeled_treetops > 0))

    # Convert local tree top coordinates to UTM32N
    utm_tree_coords = local_to_utm(tree_top_coords, transform)

    # Get tree heights corresponding to the detected tree tops
    tree_heights = [smoothed_ndsm[row, col] for row, col in tree_top_coords]

    # Combine UTM32N coordinates with tree heights
    utm_tree_data = [(x, y, height) for (x, y), height in zip(utm_tree_coords, tree_heights)]

    # Mask negative values from the nDSM (anything below 0)
    masked_ndsm = np.ma.masked_where(smoothed_ndsm < 0, smoothed_ndsm)

    # Dynamically set vmin and vmax based on the valid (non-masked) data
    valid_ndsm = smoothed_ndsm[smoothed_ndsm > 0]
    vmin_value = np.min(valid_ndsm)
    vmax_value = np.max(valid_ndsm)

    # Create a custom grayscale colormap where masked values (negative) are black
    cmap = plt.cm.gray
    cmap.set_bad(color='black')

    # Plot the nDSM and detected tree tops
    fig, ax = plt.subplots(figsize=(10, 10))
    img = ax.imshow(masked_ndsm, cmap=cmap, vmin=vmin_value, vmax=vmax_value, alpha=0.8)

    # Overlay detected tree tops as scatter points
    if len(tree_top_coords) > 0:
        ax.scatter(tree_top_coords[:, 1], tree_top_coords[:, 0], color='red', marker='o', s=5, label='Tree Tops')

    # Add a grayscale colorbar
    cbar = fig.colorbar(img, ax=ax)
    cbar.set_label('Elevation (m)')
    cbar.ax.yaxis.set_tick_params(color='black')
    cbar.outline.set_edgecolor('black')

    ax.set_title(f'Detected Tree Tops taller than {min_height_threshold} meters: {num_features}')
    ax.legend()

    # Return the UTM32N coordinates, Figure, and Axes for customization and saving
    return utm_tree_data, fig, ax




