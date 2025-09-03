import numpy as np


def _JRC2018U_mirror(pt):
    """Mirrors a 3D point across the JRC2018U template's midline.

    Args:
        pt (np.ndarray): A 3D point coordinate (x, y, z).

    Returns:
        np.ndarray: The mirrored 3D point coordinate.
    """
    return np.array([627 - pt[0], pt[1], pt[2]])


def centroid_matching(user_centroid, loader):
    """Finds the closest hemilineages to a user-provided centroid.

    This function calculates the Euclidean distance from a user-specified 3D
    point to the pre-calculated centroids of all hemilineages. It considers
    both the original point and its mirrored version across the brain's
    midline to account for bilateral symmetry. A match is considered valid if
    the distance is within three times the Root Sum of Squares of Error (RMSE)
    of the hemilineage's own cell body distribution.

    Args:
        user_centroid (tuple or np.ndarray): The (x, y, z) coordinates of the
            point selected by the user.
        loader (object): An instance of a data loader class that provides
            access to the hemilineage soma data via a `get_somas()` method.

    Returns:
        dict: A dictionary containing the user's centroid and a list of
            matching hemilineage names, sorted by distance. For example:
            {
                'user_centroid': (123.4, 567.8, 90.1),
                'hemilineages': ['hemilineage_A', 'hemilineage_B']
            }

    Raises:
        ValueError: If the DataFrame returned by the loader does not contain
            the required columns.
    """

    df = loader.get_somas()
    print("successfully loaded somas")
    # Ensure columns: hemilineage, centroid_x, centroid_y, centroid_z, 3*RMSE
    required_cols = {
        "ito_lee_hemilineage",
        "centroid_x",
        "centroid_y",
        "centroid_z",
        "3*RMSE",
    }
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")
    print("successfully validated columns")

    # Compute distances from user_centroid to each hemilineage centroid
    hemilineage_coords = df[["centroid_x", "centroid_y", "centroid_z"]].values
    user_coords = np.array(user_centroid)
    distances = np.linalg.norm(hemilineage_coords - user_coords, axis=1)
    # compare mirrored distances just incase user click on the left side
    mirrored_user_coords = _JRC2018U_mirror(user_coords)
    mirrored_distances = np.linalg.norm(
        hemilineage_coords - mirrored_user_coords, axis=1
    )
    df["distance"] = np.minimum(distances, mirrored_distances)
    # print min and max of distance
    print(f"Min distance: {df['distance'].min()}")
    print(f"Max distance: {df['distance'].max()}")

    matches = df[df["distance"] <= df["3*RMSE"]].copy()
    matches = matches.sort_values("distance")

    hemilineage_names = matches["ito_lee_hemilineage"].tolist()
    return {
        "user_centroid": tuple(float(c) for c in user_centroid),
        "hemilineages": hemilineage_names,
    }
