# src/top_hat/core/voxel_counting.py

import numpy as np


def count_voxels(query: np.ndarray, target: np.ndarray) -> float:
    """Count the overlapped voxels between query and target. Normalized by the
    total number of voxels in the target."""
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
    """Count the overlapped voxels between query and each target in the hemilineage."""
    iterable = target_list
    results = {}
    if progress_wrapper:
        iterable = progress_wrapper(
            target_list,
            desc="Counting overlap voxels:",
        )
    for target_name in iterable:
        target = loader.get_hat_bundles_nrrd(target_name)
        if target is not None:
            results[target_name] = count_voxels(query, target)
    return results
