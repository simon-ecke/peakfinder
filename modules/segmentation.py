
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
    show_contours=False,
    return_arrays=False  # new parameter to control if data arrays are returned
):
    if threshold_abs is None:
        threshold_abs = ground_threshold

    # Load the nDSM file
    with rasterio.open(ndsm_path) as src:
        ndsm = src.read(1)
        ndsm_profile = src.profile
        transform = src.transform

    # Extract raster resolution and calculate pixel size
    pixel_size_x = abs(ndsm_profile['transform'][0])
    pixel_size_y = abs(ndsm_profile['transform'][4])

    # Decide which area to process: full or subset
    if use_subset:
        subset_size_pixels_x = int(subset_size_meters / pixel_size_x)
        subset_size_pixels_y = int(subset_size_meters / pixel_size_y)

        center_x = ndsm.shape[1] // 2
        center_y = ndsm.shape[0] // 2

        start_x = center_x - subset_size_pixels_x // 2
        start_y = center_y - subset_size_pixels_y // 2
        end_x = start_x + subset_size_pixels_x
        end_y = start_y + subset_size_pixels_y

        ndsm_subset = ndsm[start_y:end_y, start_x:end_x]
    else:
        ndsm_subset = ndsm

    # Threshold to remove ground and noise
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

    # Create markers from treetop locations
    markers = np.zeros_like(ndsm_subset, dtype=int)
    for i, (r, c) in enumerate(treetop_coords):
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
    plt.imshow(ndsm_subset, cmap='gray', origin='upper')
    plt.imshow(overlay, alpha=0.4)
    # Plot treetops
    rows, cols = treetop_coords[:, 0], treetop_coords[:, 1]
    plt.scatter(cols, rows, c='purple', marker='o', s=25, edgecolors='black', linewidths=0.5, label='Treetops')

    if show_contours:
        boundaries = segmentation.find_boundaries(labels, mode='thin')
        plt.contour(boundaries.astype(float), levels=[0.5], colors='red', linewidths=1)

    plt.axis('off')
    plt.legend()
    plt.show()

    if return_arrays:
        # Returning arrays and transformation for further processing
        return labels, treetop_coords, ndsm_subset, transform


def match_and_visualize(
    labels,
    treetop_coords,
    stem_coords,
    ndsm,
    transform
):
    """
    Match stem coordinates with tree tops based on segmentation and visualize the results.

    Parameters:
    -----------
    labels : np.ndarray
        Segmentation labels array (each segment has a unique integer value).
    treetop_coords : np.ndarray
        Array of tree top coordinates as (row, col) in pixel space.
    stem_coords : list of tuples
        List of stem coordinates as (layer, id, x_utm, y_utm).
    ndsm : np.ndarray
        nDSM array used for visualization.
    transform : rasterio.Affine
        Affine transform for converting UTM to pixel coordinates.

    Returns:
    --------
    matched_list : list
        List of dictionaries containing matched stem and tree top details:
        {
            "Parzelle": int,
            "Nr": int,
            "Stem_UTM_X": float,
            "Stem_UTM_Y": float,
            "Treetop_UTM_X": float,
            "Treetop_UTM_Y": float,
            "Tree_Height": float
        }
    """
    # Step 1: Extract x, y UTM coordinates from stem_coords and convert to pixel indices
    stem_coords_pixel = [
        (rasterio.transform.rowcol(transform, x, y), parzelle, nr, x, y)
        for parzelle, nr, x, y in stem_coords
    ]

    # Step 2: Create a dictionary to map segment IDs to treetops and stems
    segment_to_treetops = {}
    segment_to_stems = {}

    for r_treetop, c_treetop in treetop_coords:
        segment_id = labels[r_treetop, c_treetop]
        if segment_id > 0:  # Ignore background (label 0)
            if segment_id not in segment_to_treetops:
                segment_to_treetops[segment_id] = []
            segment_to_treetops[segment_id].append((r_treetop, c_treetop))

    for (r_stem, c_stem), parzelle, nr, x, y in stem_coords_pixel:
        if 0 <= r_stem < labels.shape[0] and 0 <= c_stem < labels.shape[1]:
            segment_id = labels[r_stem, c_stem]
            if segment_id > 0:  # Ignore background (label 0)
                if segment_id not in segment_to_stems:
                    segment_to_stems[segment_id] = []
                segment_to_stems[segment_id].append((r_stem, c_stem, parzelle, nr, x, y))

    # Step 3: Find segments with exactly one stem and one tree top
    matched_list = []
    unmatched_stems = []

    for segment_id, stems in segment_to_stems.items():
        treetops = segment_to_treetops.get(segment_id, [])
        if len(stems) == 1 and len(treetops) == 1:
            r_treetop, c_treetop = treetops[0]
            r_stem, c_stem, parzelle, nr, x_stem, y_stem = stems[0]

            # Convert treetop pixel coordinates to UTM
            utm_x_treetop, utm_y_treetop = rasterio.transform.xy(transform, r_treetop, c_treetop, offset="center")
            tree_height = ndsm[r_treetop, c_treetop]  # Tree height directly from the nDSM

            # Add matched pair to the list
            matched_list.append({
                "Parzelle": parzelle,
                "Nr": nr,
                "Stem_UTM_X": x_stem,
                "Stem_UTM_Y": y_stem,
                "Treetop_UTM_X": utm_x_treetop,
                "Treetop_UTM_Y": utm_y_treetop,
                "Tree_Height": tree_height
            })
        else:
            # Add unmatched stems to the list
            unmatched_stems.extend(stems)

    # Step 4: Visualization
    plt.figure(figsize=(20, 20))
    plt.imshow(ndsm, cmap='gray', origin='upper')
    plt.title("Stem Matching Visualization", fontsize=20)

    # Plot matched stems in green
    for match in matched_list:
        r, c = rasterio.transform.rowcol(transform, match["Stem_UTM_X"], match["Stem_UTM_Y"])
        plt.scatter(
            c, r, color='green', label='Matched Stem', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot unmatched stems in red
    for r_stem, c_stem, _, _, _, _ in unmatched_stems:
        plt.scatter(
            c_stem, r_stem, color='red', label='Unmatched Stem', s=50, edgecolors='black', linewidths=0.5
        )

    # Remove duplicate labels in the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), fontsize=12)

    plt.axis('off')
    plt.show()

    return matched_list



def match_and_visualize_all(
    labels,
    treetop_coords,
    stem_coords,
    ndsm,
    transform
):
    """
    Match stem coordinates with tree tops based on segmentation and visualize the results.

    Parameters:
    -----------
    labels : np.ndarray
        Segmentation labels array (each segment has a unique integer value).
    treetop_coords : np.ndarray
        Array of tree top coordinates as (row, col) in pixel space.
    stem_coords : list of tuples
        List of stem coordinates as (layer, id, x_utm, y_utm).
    ndsm : np.ndarray
        nDSM array used for visualization.
    transform : rasterio.Affine
        Affine transform for converting UTM to pixel coordinates.

    Returns:
    --------
    matched_list : list
        List of dictionaries containing matched stem and tree top details:
        {
            "Parzelle": int,
            "Nr": int,
            "Stem_UTM_X": float,
            "Stem_UTM_Y": float,
            "Treetop_UTM_X": float,
            "Treetop_UTM_Y": float,
            "Tree_Height": float
        }
    """
    # Step 1: Extract x, y UTM coordinates from stem_coords and convert to pixel indices
    stem_coords_pixel = [
        (rasterio.transform.rowcol(transform, x, y), parzelle, nr, x, y)
        for parzelle, nr, x, y in stem_coords
    ]

    # Step 2: Create dictionaries for mapping segment IDs to treetops and stems
    segment_to_treetops = {}
    segment_to_stems = {}
    unmatched_treetops = []
    no_segment_stems = []

    # Map tree tops to segments
    for r_treetop, c_treetop in treetop_coords:
        segment_id = labels[r_treetop, c_treetop]
        if segment_id > 0:  # Tree top has a segment
            if segment_id not in segment_to_treetops:
                segment_to_treetops[segment_id] = []
            segment_to_treetops[segment_id].append((r_treetop, c_treetop))
        else:  # Tree top does not belong to any segment
            unmatched_treetops.append((r_treetop, c_treetop))

    # Map stems to segments
    for (r_stem, c_stem), parzelle, nr, x, y in stem_coords_pixel:
        if 0 <= r_stem < labels.shape[0] and 0 <= c_stem < labels.shape[1]:
            segment_id = labels[r_stem, c_stem]
            if segment_id > 0:  # Stem has a segment
                if segment_id not in segment_to_stems:
                    segment_to_stems[segment_id] = []
                segment_to_stems[segment_id].append((r_stem, c_stem, parzelle, nr, x, y))
            else:  # Stem does not belong to any segment
                no_segment_stems.append((r_stem, c_stem, parzelle, nr, x, y))

    # Step 3: Find segments with exactly one stem and one tree top
    matched_list = []
    unmatched_stems = []

    for segment_id, stems in segment_to_stems.items():
        treetops = segment_to_treetops.get(segment_id, [])
        if len(stems) == 1 and len(treetops) == 1:
            r_treetop, c_treetop = treetops[0]
            r_stem, c_stem, parzelle, nr, x_stem, y_stem = stems[0]

            # Convert treetop pixel coordinates to UTM
            utm_x_treetop, utm_y_treetop = rasterio.transform.xy(transform, r_treetop, c_treetop, offset="center")
            tree_height = ndsm[r_treetop, c_treetop]  # Tree height directly from the nDSM

            # Add matched pair to the list
            matched_list.append({
                "Parzelle": parzelle,
                "Nr": nr,
                "Stem_UTM_X": x_stem,
                "Stem_UTM_Y": y_stem,
                "Treetop_UTM_X": utm_x_treetop,
                "Treetop_UTM_Y": utm_y_treetop,
                "UAV_Tree_Height_pixel": tree_height
            })
        else:
            # Add unmatched stems to the list
            unmatched_stems.extend(stems)

    # Step 4: Visualization
    plt.figure(figsize=(20, 20))
    plt.imshow(ndsm, cmap='gray', origin='upper')
    plt.title("Stem Matching Visualization", fontsize=20)

    # Plot matched stems in green
    for match in matched_list:
        r, c = rasterio.transform.rowcol(transform, match["Stem_UTM_X"], match["Stem_UTM_Y"])
        plt.scatter(
            c, r, color='green', label='Matched Stem', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot unmatched stems in red
    for r_stem, c_stem, _, _, _, _ in unmatched_stems:
        plt.scatter(
            c_stem, r_stem, color='red', label='Unmatched Stem', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot stems with no segments in purple
    for r_stem, c_stem, _, _, _, _ in no_segment_stems:
        plt.scatter(
            c_stem, r_stem, color='purple', label='Stem without Segment', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot unmatched tree tops in blue
    for r_treetop, c_treetop in unmatched_treetops:
        plt.scatter(
            c_treetop, r_treetop, color='blue', label='Tree Top without Segment', s=50, edgecolors='black', linewidths=0.5
        )

    # Remove duplicate labels in the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), fontsize=12)

    plt.axis('off')
    plt.show()

    return matched_list

def match_and_visualize_updated(
    labels,
    treetop_coords,
    stem_coords,
    ndsm,
    transform
):
    """
    Match stem coordinates with tree tops based on segmentation and visualize the results.

    Parameters:
    -----------
    labels : np.ndarray
        Segmentation labels array (each segment has a unique integer value).
    treetop_coords : np.ndarray
        Array of tree top coordinates as (row, col) in pixel space.
    stem_coords : list of tuples
        List of stem coordinates as (layer, id, x_utm, y_utm).
    ndsm : np.ndarray
        nDSM array used for visualization.
    transform : rasterio.Affine
        Affine transform for converting UTM to pixel coordinates.

    Returns:
    --------
    matched_list : list
        List of dictionaries containing matched stem and tree top details:
        {
            "Parzelle": int,
            "Nr": int,
            "Stem_UTM_X": float,
            "Stem_UTM_Y": float,
            "Treetop_UTM_X": float,
            "Treetop_UTM_Y": float,
            "Tree_Height": float
        }
    """
    # Step 1: Extract x, y UTM coordinates from stem_coords and convert to pixel indices
    stem_coords_pixel = [
        (rasterio.transform.rowcol(transform, x, y), parzelle, nr, x, y)
        for parzelle, nr, x, y in stem_coords
    ]

    # Step 2: Create dictionaries for mapping segment IDs to treetops and stems
    segment_to_treetops = {}
    segment_to_stems = {}
    unmatched_treetops = []
    no_segment_stems = []

    # Map tree tops to segments
    for r_treetop, c_treetop in treetop_coords:
        segment_id = labels[r_treetop, c_treetop]
        if segment_id > 0:  # Tree top has a segment
            if segment_id not in segment_to_treetops:
                segment_to_treetops[segment_id] = []
            segment_to_treetops[segment_id].append((r_treetop, c_treetop))
        else:  # Tree top does not belong to any segment
            unmatched_treetops.append((r_treetop, c_treetop))

    # Map stems to segments
    for (r_stem, c_stem), parzelle, nr, x, y in stem_coords_pixel:
        if 0 <= r_stem < labels.shape[0] and 0 <= c_stem < labels.shape[1]:
            segment_id = labels[r_stem, c_stem]
            if segment_id > 0:  # Stem has a segment
                if segment_id not in segment_to_stems:
                    segment_to_stems[segment_id] = []
                segment_to_stems[segment_id].append((r_stem, c_stem, parzelle, nr, x, y))
            else:  # Stem does not belong to any segment
                no_segment_stems.append((r_stem, c_stem, parzelle, nr, x, y))

    # Step 3: Find segments with exactly one stem and one tree top
    matched_list = []
    unmatched_stems = []

    for segment_id, stems in segment_to_stems.items():
        treetops = segment_to_treetops.get(segment_id, [])
        if len(stems) == 1 and len(treetops) == 1:
            # Get the single stem and treetop
            r_treetop, c_treetop = treetops[0]
            r_stem, c_stem, parzelle, nr, x_stem, y_stem = stems[0]

            # Refine the tree height by finding the highest point in the segment
            segment_mask = labels == segment_id
            segment_ndsm = np.where(segment_mask, ndsm, -np.inf)  # Mask other segments as -inf
            max_idx = np.unravel_index(np.argmax(segment_ndsm), segment_ndsm.shape)
            refined_r, refined_c = max_idx
            max_height = ndsm[refined_r, refined_c]

            # Convert refined tree top pixel coordinates to UTM
            utm_x_treetop, utm_y_treetop = rasterio.transform.xy(transform, refined_r, refined_c, offset="center")

            # Add matched pair to the list
            matched_list.append({
                "Parzelle": parzelle,
                "Nr": nr,
                "Stem_UTM_X": x_stem,
                "Stem_UTM_Y": y_stem,
                "Treetop_UTM_X": utm_x_treetop,
                "Treetop_UTM_Y": utm_y_treetop,
                "Tree_Height": max_height
            })
        else:
            # Add unmatched stems to the list
            unmatched_stems.extend(stems)

    # Step 4: Visualization
    plt.figure(figsize=(20, 20))
    plt.imshow(ndsm, cmap='gray', origin='upper')
    plt.title("Stem Matching Visualization", fontsize=20)

    # Plot matched stems in green
    for match in matched_list:
        r, c = rasterio.transform.rowcol(transform, match["Stem_UTM_X"], match["Stem_UTM_Y"])
        plt.scatter(
            c, r, color='green', label='Matched Stem', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot unmatched stems in red
    for r_stem, c_stem, _, _, _, _ in unmatched_stems:
        plt.scatter(
            c_stem, r_stem, color='red', label='Unmatched Stem', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot stems with no segments in purple
    for r_stem, c_stem, _, _, _, _ in no_segment_stems:
        plt.scatter(
            c_stem, r_stem, color='purple', label='Stem without Segment', s=50, edgecolors='black', linewidths=0.5
        )

    # Plot unmatched tree tops in blue
    for r_treetop, c_treetop in unmatched_treetops:
        plt.scatter(
            c_treetop, r_treetop, color='blue', label='Tree Top without Segment', s=50, edgecolors='black', linewidths=0.5
        )

    # Remove duplicate labels in the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), fontsize=12)

    plt.axis('off')
    plt.show()

    return matched_list



def match_and_visualize_updated2(
    labels,
    treetop_coords,
    stem_coords,
    ndsm,
    transform
):
    """
    Match stem coordinates with tree tops based on segmentation and visualize the results.

    Parameters:
    -----------
    labels : np.ndarray
        Segmentation labels array (each segment has a unique integer value).
    treetop_coords : np.ndarray
        Array of tree top coordinates as (row, col) in pixel space.
    stem_coords : list of tuples
        List of stem coordinates as (layer, id, x_utm, y_utm).
    ndsm : np.ndarray
        nDSM array used for visualization.
    transform : rasterio.Affine
        Affine transform for converting UTM to pixel coordinates.

    Returns:
    --------
    result_list : list
        List of dictionaries containing stem and tree top details with a "match" column:
        {
            "Parzelle": int,
            "Nr": int,
            "Stem_UTM_X": float,
            "Stem_UTM_Y": float,
            "Treetop_UTM_X": float or None,
            "Treetop_UTM_Y": float or None,
            "Tree_Height": float or None,
            "match": int  # 1 (matched), 0 (unmatched), 2 (no segment)
        }
    """
    # Step 1: Extract x, y UTM coordinates from stem_coords and convert to pixel indices
    stem_coords_pixel = [
        (rasterio.transform.rowcol(transform, x, y), parzelle, nr, x, y)
        for parzelle, nr, x, y in stem_coords
    ]

    # Step 2: Create dictionaries for mapping segment IDs to treetops and stems
    segment_to_treetops = {}
    segment_to_stems = {}
    unmatched_treetops = []

    # Map tree tops to segments
    for r_treetop, c_treetop in treetop_coords:
        segment_id = labels[r_treetop, c_treetop]
        if segment_id > 0:  # Tree top has a segment
            if segment_id not in segment_to_treetops:
                segment_to_treetops[segment_id] = []
            segment_to_treetops[segment_id].append((r_treetop, c_treetop))
        else:  # Tree top does not belong to any segment
            unmatched_treetops.append((r_treetop, c_treetop))

    # Map stems to segments
    for (r_stem, c_stem), parzelle, nr, x, y in stem_coords_pixel:
        if 0 <= r_stem < labels.shape[0] and 0 <= c_stem < labels.shape[1]:
            segment_id = labels[r_stem, c_stem]
            if segment_id > 0:  # Stem has a segment
                if segment_id not in segment_to_stems:
                    segment_to_stems[segment_id] = []
                segment_to_stems[segment_id].append((r_stem, c_stem, parzelle, nr, x, y))
            else:  # Stem does not belong to any segment
                segment_to_stems["no_segment"] = segment_to_stems.get("no_segment", []) + [
                    (r_stem, c_stem, parzelle, nr, x, y)
                ]

    # Step 3: Create the result list
    result_list = []

    for segment_id, stems in segment_to_stems.items():
        treetops = segment_to_treetops.get(segment_id, [])
        if segment_id == "no_segment":
            for r_stem, c_stem, parzelle, nr, x, y in stems:
                result_list.append({
                    "Parzelle": parzelle,
                    "Nr": nr,
                    "Stem_UTM_X": x,
                    "Stem_UTM_Y": y,
                    "Treetop_UTM_X": None,
                    "Treetop_UTM_Y": None,
                    "UAV_Tree_Height_segment": None,
                    "match": 2  # Stem without segment
                })
        elif len(stems) == 1 and len(treetops) == 1:
            # Get the single stem and treetop
            r_treetop, c_treetop = treetops[0]
            r_stem, c_stem, parzelle, nr, x_stem, y_stem = stems[0]

            # Refine the tree height by finding the highest point in the segment
            segment_mask = labels == segment_id
            segment_ndsm = np.where(segment_mask, ndsm, -np.inf)  # Mask other segments as -inf
            max_idx = np.unravel_index(np.argmax(segment_ndsm), segment_ndsm.shape)
            refined_r, refined_c = max_idx
            max_height = ndsm[refined_r, refined_c]

            # Convert refined tree top pixel coordinates to UTM
            utm_x_treetop, utm_y_treetop = rasterio.transform.xy(transform, refined_r, refined_c, offset="center")

            # Add matched pair to the result list
            result_list.append({
                "Parzelle": parzelle,
                "Nr": nr,
                "Stem_UTM_X": x_stem,
                "Stem_UTM_Y": y_stem,
                "Treetop_UTM_X": utm_x_treetop,
                "Treetop_UTM_Y": utm_y_treetop,
                "UAV_Tree_Height_segment": max_height,
                "match": 1  # Matched
            })
        else:
            # Add unmatched stems to the result list
            for r_stem, c_stem, parzelle, nr, x, y in stems:
                result_list.append({
                    "Parzelle": parzelle,
                    "Nr": nr,
                    "Stem_UTM_X": x,
                    "Stem_UTM_Y": y,
                    "Treetop_UTM_X": None,
                    "Treetop_UTM_Y": None,
                    "UAV_Tree_Height_segment": None,
                    "match": 0  # Unmatched
                })

    # Step 4: Visualization
    plt.figure(figsize=(20, 20))
    plt.imshow(ndsm, cmap='gray', origin='upper')
    plt.title("Stem Matching Visualization", fontsize=20)

    # Plot stems based on match status
    for result in result_list:
        r, c = rasterio.transform.rowcol(transform, result["Stem_UTM_X"], result["Stem_UTM_Y"])
        if result["match"] == 1:
            color, label = "green", "Matched Stem"
        elif result["match"] == 0:
            color, label = "red", "Unmatched Stem"
        else:
            color, label = "purple", "Stem without Segment"
        plt.scatter(c, r, color=color, label=label, s=50, edgecolors='black', linewidths=0.5)

    # Plot unmatched tree tops in blue
    for r_treetop, c_treetop in unmatched_treetops:
        plt.scatter(
            c_treetop, r_treetop, color="blue", label="Tree Top without Segment", s=50, edgecolors="black", linewidths=0.5
        )

    # Remove duplicate labels in the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), fontsize=12)

    plt.axis("off")
    plt.show()

    return result_list
