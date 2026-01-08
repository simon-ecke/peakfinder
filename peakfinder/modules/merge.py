
import numpy as np
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt
import rasterio

def match_stems_to_treetops(stems, treetops, max_distance=1.5):
    """
    Matches tree stems to their closest treetops with a distance limitation, ensuring unique global matches.

    Args:
        stems (list): List of stem data (Parzelle, Nr, utm_x, utm_y).
        treetops (list): List of treetop data (utm_x, utm_y, tree_height).
        max_distance (float): Maximum allowed distance (both x and y) for matching.

    Returns:
        list: List of matched data (Parzelle, Nr, stem_x, stem_y, top_x, top_y, tree_height).
    """
    n_stems = len(stems)
    n_treetops = len(treetops)

    # Create a cost matrix for distances
    cost_matrix = np.full((n_stems, n_treetops), np.inf)  # Initialize with large values

    for i, stem in enumerate(stems):
        _, _, stem_x, stem_y = stem
        for j, (top_x, top_y, _) in enumerate(treetops):
            dist = np.sqrt((stem_x - top_x) ** 2 + (stem_y - top_y) ** 2)
            if dist <= max_distance:  # Only consider matches within max_distance
                cost_matrix[i, j] = dist

    # Exclude rows and columns with all np.inf
    valid_stem_indices = np.any(cost_matrix != np.inf, axis=1)
    valid_treetop_indices = np.any(cost_matrix != np.inf, axis=0)

    reduced_cost_matrix = cost_matrix[np.ix_(valid_stem_indices, valid_treetop_indices)]

    # Check if there are valid rows and columns
    if reduced_cost_matrix.size == 0 or not np.any(reduced_cost_matrix != np.inf):
        # If no matches are possible, return all stems as unmatched
        return [(parzelle, nr, stem_x, stem_y, None, None, None) for parzelle, nr, stem_x, stem_y in stems]

    # Solve the assignment problem using the Hungarian algorithm for valid rows/columns
    row_indices, col_indices = linear_sum_assignment(reduced_cost_matrix)

    # Map reduced indices back to the original stems and treetops
    matched_data = []
    used_treetops = set()
    for row_idx, col_idx in zip(row_indices, col_indices):
        if reduced_cost_matrix[row_idx, col_idx] != np.inf:
            original_stem_idx = np.where(valid_stem_indices)[0][row_idx]
            original_treetop_idx = np.where(valid_treetop_indices)[0][col_idx]

            parzelle, nr, stem_x, stem_y = stems[original_stem_idx]
            top_x, top_y, tree_height = treetops[original_treetop_idx]

            matched_data.append((parzelle, nr, stem_x, stem_y, top_x, top_y, tree_height))
            used_treetops.add(original_treetop_idx)

    # Add unmatched stems
    unmatched_stems = np.where(~valid_stem_indices)[0]
    for idx in unmatched_stems:
        parzelle, nr, stem_x, stem_y = stems[idx]
        matched_data.append((parzelle, nr, stem_x, stem_y, None, None, None))

    return matched_data

def process_unmatched_stems(matched_data, treetops, radius=5.0):
    """
    Processes unmatched stems to check for isolated cases where a single treetop exists within a radius.

    Args:
        matched_data (list): List of matched data from the first function.
        treetops (list): List of treetop data (utm_x, utm_y, tree_height).
        radius (float): Radius within which to check for isolated treetops.

    Returns:
        list: Updated matched data with additional matches for isolated cases.
    """
    # Identify treetops already matched
    matched_treetops = {
        (stem[4], stem[5]) for stem in matched_data if stem[4] is not None and stem[5] is not None
    }

    # Identify unmatched stems
    unmatched_stems = [stem for stem in matched_data if stem[4] is None]
    updated_data = matched_data.copy()

    for unmatched_stem in unmatched_stems:
        parzelle, nr, stem_x, stem_y, _, _, _ = unmatched_stem

        # Find nearby treetops within the radius
        nearby_treetops = [
            (top_x, top_y, tree_height)
            for top_x, top_y, tree_height in treetops
            if np.sqrt((stem_x - top_x) ** 2 + (stem_y - top_y) ** 2) <= radius
            and (top_x, top_y) not in matched_treetops  # Exclude already matched treetops
        ]

        # If exactly one treetop is within the radius, consider it a match
        if len(nearby_treetops) == 1:
            top_x, top_y, tree_height = nearby_treetops[0]
            matched_treetops.add((top_x, top_y))  # Mark treetop as matched

            # Update the matched data
            updated_data = [
                (parzelle, nr, stem_x, stem_y, top_x, top_y, tree_height) if stem == unmatched_stem else stem
                for stem in updated_data
            ]

    return updated_data


def visualize_matched_trees(stems, parzelle_number=1):
    """
    Visualize stems for a given Parzelle number, where matched stems are green and unmatched stems are red.

    Args:
        stems (list of tuples): 
            [(Parzelle, Nr, stem_x, stem_y, top_x, top_y, tree_height), ...]
            - If `top_x`, `top_y`, and `tree_height` are None, the stem is unmatched.
        parzelle_number (int): The Parzelle number to visualize.
    """
    # Filter for the specified Parzelle
    selected_stems = [stem for stem in stems if stem[0] == parzelle_number]

    # Separate matched and unmatched stems
    matched_stems = [stem for stem in selected_stems if stem[4] is not None]
    unmatched_stems = [stem for stem in selected_stems if stem[4] is None]

    # Prepare data for plotting
    matched_x = [stem[2] for stem in matched_stems]
    matched_y = [stem[3] for stem in matched_stems]
    unmatched_x = [stem[2] for stem in unmatched_stems]
    unmatched_y = [stem[3] for stem in unmatched_stems]

    # Create the plot
    plt.figure(figsize=(10, 8))

    # Plot matched stems
    plt.scatter(matched_x, matched_y, color="green", label="Matched Stems")

    # Plot unmatched stems
    plt.scatter(unmatched_x, unmatched_y, color="red", label="Unmatched Stems")

    # Labels, legend, and grid
    plt.xlabel("UTM_x")
    plt.ylabel("UTM_y")
    plt.title(f"Visualization of Stems in Parzelle {parzelle_number}")
    plt.legend()
    plt.grid(True)

    # Show the plot
    plt.show()


def visualize_ndsm_with_trees(ndsm_path, stems):
    """
    Visualize the nDSM raster with matched and unmatched stems overlaid.

    Args:
        ndsm_path (str): File path to the nDSM raster.
        stems (list of tuples): 
            [(Parzelle, Nr, stem_x, stem_y, top_x, top_y, tree_height), ...]
            - Matched stems: Non-None top_x, top_y, tree_height.
            - Unmatched stems: None values in top_x, top_y, tree_height.
    """
    # Open the nDSM raster
    with rasterio.open(ndsm_path) as src:
        ndsm_data = src.read(1)  # Read the first band
        ndsm_transform = src.transform

    # Separate matched and unmatched stems
    matched_stems = [stem for stem in stems if stem[4] is not None]
    unmatched_stems = [stem for stem in stems if stem[4] is None]

    # Extract matched coordinates
    matched_x = [stem[2] for stem in matched_stems]  # top_x
    matched_y = [stem[3] for stem in matched_stems]  # top_y

    # Extract unmatched coordinates
    unmatched_x = [stem[2] for stem in unmatched_stems]  # stem_x
    unmatched_y = [stem[3] for stem in unmatched_stems]  # stem_y

    # Plot the nDSM
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(ndsm_data, cmap="gray", extent=(
        ndsm_transform[2],  # left
        ndsm_transform[2] + ndsm_transform[0] * ndsm_data.shape[1],  # right
        ndsm_transform[5] + ndsm_transform[4] * ndsm_data.shape[0],  # bottom
        ndsm_transform[5]  # top
    ))

    # Overlay matched stems in green
    ax.scatter(matched_x, matched_y, color="green", label="Matched Trees", s=20, edgecolors="black")

    # Overlay unmatched stems in red
    ax.scatter(unmatched_x, unmatched_y, color="red", label="Unmatched Trees", s=20, edgecolors="black")

    # Labels and legend
    ax.set_xlabel("UTM_x")
    ax.set_ylabel("UTM_y")
    ax.set_title("nDSM with Matched and Unmatched Trees Overlay")
    ax.legend()
    ax.grid(False)

    # Show the combined plot
    plt.show()


def merge_dictionaries(results, matched_stems):
    """
    Merges two dictionaries based on "Parzelle" and "Nr", adding "UAV_Tree_Height_pixel"
    from matched_stems to results.

    Parameters:
    -----------
    results : list of dicts
        List of dictionaries containing the results data.
    matched_stems : list of dicts
        List of dictionaries containing matched stems with "UAV_Tree_Height_pixel".

    Returns:
    --------
    merged_results : list of dicts
        Updated results with the "UAV_Tree_Height_pixel" column added.
    """
    # Convert matched_stems into a lookup dictionary for quick access
    matched_lookup = {
        (item["Parzelle"], item["Nr"]): item["UAV_Tree_Height_pixel"]
        for item in matched_stems
    }

    # Add "UAV_Tree_Height_pixel" to results
    for result in results:
        key = (result["Parzelle"], result["Nr"])
        result["UAV_Tree_Height_pixel"] = matched_lookup.get(key, None)  # Add value or None if not found

    return results

