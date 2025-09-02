import numpy as np


def _JRC2018U_mirror(pt):
    """Mirror a point across the midline. Assuming pt is a 3D point (x, y, z)."""
    return np.array([627 - pt[0], pt[1], pt[2]])


def centroid_matching(user_centroid, loader):
    """Match a user-provided centroid to the closest hemilineages
    based on their centroids."""

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
