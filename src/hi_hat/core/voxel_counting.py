import numpy as np


def count_voxels(query: np.ndarray, target: np.ndarray) -> float:
    """Counts the overlapping voxels between a query and a target array.

    The result is normalized by the total number of non-zero voxels in the
    target array. Both arrays are expected to be binary (containing 0s and 1s).

    Args:
        query (np.ndarray): A NumPy array representing the query object.
        target (np.ndarray): A NumPy array representing the target object.
            Must have the same shape as the query array.

    Returns:
        float: The ratio of overlapping voxels to the total voxels in the
            target. Returns 0.0 if the target has no voxels.

    Raises:
        ValueError: If the query and target arrays do not have the same shape.
    """
    # check if two arrays have the same shape
    if query.shape != target.shape:
        raise ValueError("Query and target must have the same shape.")

    overlap = np.sum(np.logical_and(query, target))
    target_voxels = np.sum(target)
    return overlap / target_voxels if target_voxels > 0 else 0.0


def count_voxels_in_hemilineage(
    query: np.ndarray,
    target_list: list[str],
    loader: any,
    progress_wrapper=None,
) -> dict:
    """Counts overlapping voxels between a query and multiple hemilineage targets.

    This function iterates through a list of target hemilineage names, loads
    their corresponding data arrays, and computes the normalized voxel overlap
    with the query array.

    Args:
        query (np.ndarray): A NumPy array representing the query object.
        target_list (list[str]): A list of names of the target hemilineages.
        loader (any): An instance of a data loader class that provides access
            to hemilineage data via a `get_hat_bundles_nrrd()` method.
        progress_wrapper (callable, optional): A wrapper function (like tqdm)
            to provide progress updates for the iteration over the target list.
            Defaults to None.

    Returns:
        dict: A dictionary where keys are the target hemilineage names and
            values are their corresponding normalized voxel overlap scores.
    """
    iterable = target_list
    results = {}
    if progress_wrapper:
        iterable = progress_wrapper(
            target_list,
            desc="Counting overlap voxels:",
        )
    for target_name in iterable:
        print(f"Voxel: Processing {target_name}...")
        target = loader.get_hat_bundles_nrrd(target_name)
        if target is not None:
            results[target_name] = count_voxels(query, target)
    return results
