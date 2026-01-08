import pyodbc
import numpy as np
import matplotlib.pyplot as plt

def fetch_corners_and_trees(dsn_name, versuch_id):
    """
    Fetch corner points and tree points from the database for a specified Versuch ID.

    Args:
        dsn_name (str): The name of the DSN configured in the ODBC Data Source Administrator.
        versuch_id (int): The Versuch ID to filter the data.

    Returns:
        tuple: (corners, trees)
            - corners: List of tuples containing Parzelle, Nr, UTM_x, UTM_y.
            - trees: List of tuples containing Parzelle, Nr, x, y, z.
    """
    try:
        # Connect to the database
        conn = pyodbc.connect(f"DSN={dsn_name};")
        print("Connected to the database successfully.")

        with conn.cursor() as cursor:
            # Query to get corner points
            query_corners = f"""
            SELECT Parzelle, Nr, UTM_x, UTM_y
            FROM dbo.Objekte
            WHERE Versuch = {versuch_id} AND Nr > 10000 AND UTM_x IS NOT NULL AND UTM_y IS NOT NULL
            ORDER BY Parzelle, Nr;
            """
            cursor.execute(query_corners)
            corners = cursor.fetchall()

            # Query to get tree points
            query_trees = f"""
            SELECT Parzelle, Nr, x, y, z
            FROM dbo.Objekte
            WHERE Versuch = {versuch_id} AND Nr BETWEEN 1000 AND 9999 AND x IS NOT NULL AND y IS NOT NULL
            ORDER BY Parzelle, Nr;
            """
            cursor.execute(query_trees)
            trees = cursor.fetchall()

        print("Data retrieved successfully.")
        print(f"Corner points retrieved: {len(corners)}")
        print(f"Tree points retrieved: {len(trees)}")
        
        return corners, trees

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None


def find_ground_lines(corner_points):
    """
    Identify the lower-left and lower-right points of the ground line for all Parzellen.

    Args:
        corner_points (list of tuples): [(Parzelle, Nr, UTM_x, UTM_y), ...]

    Returns:
        dict: {Parzelle: (lower_left, lower_right)}
            - lower_left: (UTM_x, UTM_y) for the lower-left corner.
            - lower_right: (UTM_x, UTM_y) for the lower-right corner.
    """
    from collections import defaultdict
    parzellen = defaultdict(list)

    # Group corner points by Parzelle
    for point in corner_points:
        parzellen[point[0]].append(point)

    ground_lines = {}
    for parzelle, points in parzellen.items():
        # Sort by UTM_y (ascending) to find the lowest ground level (lower-left point)
        sorted_by_y = sorted(points, key=lambda p: p[3])
        lower_left = (sorted_by_y[0][2], sorted_by_y[0][3])

        # Determine the farthest point along the ground line
        lower_right = max(points, key=lambda p: p[2])  # Max UTM_x

        ground_lines[parzelle] = (lower_left, (lower_right[2], lower_right[3]))

    return ground_lines

def transform_trees_all(trees_local, ground_lines):
    """
    Transform tree coordinates for multiple Parzellen from local to UTM.

    Args:
        trees_local (list of tuples): [(Parzelle, Nr, x, y, z), ...]
        ground_lines (dict): {Parzelle: (lower_left, lower_right)}

    Returns:
        list: Transformed tree coordinates [(Parzelle, Nr, utm_x, utm_y), ...].
    """
    transformed_trees = []

    for parzelle, (utm_lower_left, utm_lower_right) in ground_lines.items():
        # Compute ground vector and perpendicular vector
        ground_vector = np.array([utm_lower_right[0] - utm_lower_left[0], utm_lower_right[1] - utm_lower_left[1]])
        ground_length = np.linalg.norm(ground_vector)
        unit_ground_vector = ground_vector / ground_length
        perpendicular_vector = np.array([-unit_ground_vector[1], unit_ground_vector[0]])

        # Transform trees for this Parzelle
        trees_parzelle = [tree for tree in trees_local if tree[0] == parzelle]
        for tree in trees_parzelle:
            _, nr, x, y, _ = tree
            utm_x = utm_lower_left[0] + x * unit_ground_vector[0] + y * perpendicular_vector[0]
            utm_y = utm_lower_left[1] + x * unit_ground_vector[1] + y * perpendicular_vector[1]
            transformed_trees.append((parzelle, nr, utm_x, utm_y))

    return transformed_trees

def visualize_all_plots(corner_points, tree_points):
    """
    Visualizes the corner points and tree points for all Plots ("Parzellen") in a single graph.

    Args:
        corner_points (list of tuples): [(Parzelle, Nr, UTM_x, UTM_y), ...]
        tree_points (list of tuples): [(Parzelle, Nr, UTM_x, UTM_y), ...]
    """
    plt.figure(figsize=(12, 10))

    # Extract corner points coordinates
    corner_x = [p[2] for p in corner_points]
    corner_y = [p[3] for p in corner_points]
    
    # Extract tree points coordinates
    tree_x = [t[2] for t in tree_points]
    tree_y = [t[3] for t in tree_points]

    # Plot all corners as blue squares
    plt.scatter(corner_x, corner_y, color="blue", label="Plots (Corners)", marker="s", s=25)

    # Plot all trees as purple dots
    plt.scatter(tree_x, tree_y, color="purple", label="Trees", alpha=0.7, s=25)

    # Labels, legend, and title
    plt.xlabel("UTM_x")
    plt.ylabel("UTM_y")
    plt.title("All Plots: Trees and Corners")
    plt.legend()
    plt.grid(True)
    plt.show()
