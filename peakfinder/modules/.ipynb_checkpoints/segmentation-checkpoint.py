
import numpy as np
import matplotlib.pyplot as plt
from skimage import segmentation, filters, feature, color
from skimage.measure import regionprops
from skimage.segmentation import relabel_sequential
from scipy import ndimage as ndi
import rasterio

def segment_trees(
    ndsm_path,
    ground_threshold=10.0,
    sigma_for_treetops=10.0,
    sigma_for_segmentation=0.25,
    min_distance=10,
    threshold_abs=None,
    exclude_border=False,
    connectivity=1,
    compactness=0.2,
    watershed_line=False,
    subset_size_meters=200,
    min_area_threshold=500,
    use_subset=True,
    show_contours=False
):
    """
    Perform tree crown segmentation on an nDSM with optional subset extraction and contour visualization.

    Parameters:
    -----------
    ndsm_path : str
        Path to the nDSM GeoTIFF file.
    ground_threshold : float, optional
        Height threshold for removing ground and low vegetation.
    sigma_for_treetops : float, optional
        Sigma for Gaussian smoothing for treetop detection.
    sigma_for_segmentation : float, optional
        Sigma for Gaussian smoothing for segmentation.
    min_distance : int, optional
        Minimum distance between detected treetops.
    threshold_abs : float or None, optional
        Absolute intensity threshold for peak detection. If None, defaults to ground_threshold.
    exclude_border : bool, optional
        If True, excludes the border of the image for treetop detection.
    connectivity : int, optional
        Connectivity for the watershed.
    compactness : float, optional
        Compactness parameter for watershed segmentation.
    watershed_line : bool, optional
        If True, returns only the watershed line.
    subset_size_meters : float, optional
        Size of the subset in meters if use_subset is True.
    min_area_threshold : int, optional
        Minimum area in pixels to keep segments.
    use_subset : bool, optional
        If True, uses a subset of the nDSM. If False, uses the entire nDSM.
    show_contours : bool, optional
        If True, overlays contour lines on the result.

    Returns:
    --------
    None
        Displays a plot of the segmented tree crowns.
    """

    if threshold_abs is None:
        threshold_abs = ground_threshold

    # Load the nDSM file
    with rasterio.open(ndsm_path) as src:
        ndsm = src.read(1)
        ndsm_profile = src.profile
        transform = src.transform

    # Extract raster resolution and calculate pixel size
    pixel_size_x = abs(ndsm_profile['transform'][0])  # Pixel size X
    pixel_size_y = abs(ndsm_profile['transform'][4])  # Pixel size Y
    print(f"Pixel size: {pixel_size_x}m x {pixel_size_y}m")

    # Decide which area to process: full or subset
    if use_subset:
        # Calculate the subset size in pixels
        subset_size_pixels_x = int(subset_size_meters / pixel_size_x)
        subset_size_pixels_y = int(subset_size_meters / pixel_size_y)

        # Determine the center of the raster
        center_x = ndsm.shape[1] // 2
        center_y = ndsm.shape[0] // 2

        # Calculate start and end indices for the subset
        start_x = center_x - subset_size_pixels_x // 2
        start_y = center_y - subset_size_pixels_y // 2
        end_x = start_x + subset_size_pixels_x
        end_y = start_y + subset_size_pixels_y

        ndsm_subset = ndsm[start_y:end_y, start_x:end_x]
    else:
        ndsm_subset = ndsm  # Use the whole raster

    # Preprocessing: Threshold to remove ground and noise
    ndsm_cleaned = np.where(ndsm_subset > ground_threshold, ndsm_subset, 0)

    # Smooth for treetop detection
    ndsm_for_treetops = filters.gaussian(ndsm_cleaned, sigma=sigma_for_treetops)

    # Smooth for segmentation
    ndsm_for_segmentation = filters.gaussian(ndsm_cleaned, sigma=sigma_for_segmentation)

    # Compute the gradient for segmentation
    gradient = filters.sobel(ndsm_for_segmentation)

    # Treetop detection
    treetop_coords = feature.peak_local_max(
        ndsm_for_treetops,
        min_distance=min_distance,
        threshold_abs=threshold_abs,
        exclude_border=exclude_border
    )

    # Extract treetop rows and columns
    rows = treetop_coords[:, 0]
    cols = treetop_coords[:, 1]

    # Create markers from treetop locations
    markers = np.zeros_like(ndsm_subset, dtype=int)
    for i, (r, c) in enumerate(zip(rows, cols)):
        if 0 <= r < markers.shape[0] and 0 <= c < markers.shape[1]:
            markers[r, c] = i + 1

    # Apply the watershed algorithm
    labels = segmentation.watershed(
        image=gradient,
        markers=markers,
        connectivity=connectivity,
        compactness=compactness,
        watershed_line=watershed_line,
        mask=ndsm_for_segmentation > 0
    )

    # Remove very small segments
    props = regionprops(labels)
    small_labels = [p.label for p in props if p.area < min_area_threshold]
    for sl in small_labels:
        labels[labels == sl] = 0

    # Relabel segments
    labels = relabel_sequential(labels)[0]

    # Create an overlay of colored segments
    overlay = color.label2rgb(labels, bg_label=0)

    # Plotting results
    plt.figure(figsize=(20, 20))
    plt.title("Segmented Tree Crowns", fontsize=20)

    # Show grayscale background
    plt.imshow(ndsm_subset, cmap='gray', origin='upper')

    # Overlay the colored labels with transparency
    plt.imshow(overlay, alpha=0.4)

    # Plot treetops
    plt.scatter(cols, rows, c='purple', marker='o', s=25, edgecolors='black', linewidths=0.5, label='Treetops')

    if show_contours:
        # Extract boundaries and plot
        boundaries = segmentation.find_boundaries(labels, mode='thin')
        plt.contour(boundaries.astype(float), levels=[0.5], colors='red', linewidths=1)

    plt.axis('off')
    plt.legend()
    plt.show()


# Example usage:
# segment_trees(ndsm_path, use_subset=False, show_contours=True)
