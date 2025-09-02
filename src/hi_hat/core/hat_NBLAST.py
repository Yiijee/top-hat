import navis


def hat_nblast(
    query_path: str,
    target_list: list[str],
    th: int,
    loader: any,
    progress_wrapper=None,
) -> dict:
    """Performs NBLAST between a query neuron and a list of target hemilineages.

    This function reads a query neuron from a file, converts it to a 'dotprops'
    representation, and then computes the NBLAST similarity score against a
    list of target hemilineage bundles.

    Args:
        query_path (str): The file path to the query neuron image (e.g., NRRD).
        target_list (list[str]): A list of names of the target hemilineages
            to compare against.
        th (int): The threshold value used to binarize the query image when
            generating dotprops.
        loader (any): An instance of a data loader class that provides access
            to hemilineage bundle data via a `get_hat_bundles_dps()` method.
        progress_wrapper (callable, optional): A wrapper function (like tqdm)
            to provide progress updates for the iteration over the target list.
            Defaults to None.

    Returns:
        dict: A dictionary where keys are the target hemilineage names and
            values are their corresponding NBLAST scores against the query.
            Example: {'hemilineage_A': 0.75, 'hemilineage_B': -0.12}
    """
    print(f"NBLAST: Making dotprops for {query_path}...")
    query_dps = navis.read_nrrd(
        query_path, output="dotprops", threshold=th, k=100, resample=1
    )
    print(f"NBLAST: Loaded {len(query_dps)} points from query.")
    query_dps = navis.drop_fluff(query_dps)
    results = {}
    iterable = target_list
    if progress_wrapper:
        iterable = progress_wrapper(
            target_list,
            desc="NBLAST",
        )
    for hat in iterable:
        print(f"NBLAST: Processing {hat}...")
        hat_bundle = loader.get_hat_bundles_dps(hat, symmetry=True)
        hat_bundle = navis.make_dotprops(hat_bundle, k=100)
        if hat_bundle is not None:
            score = navis.nblast_smart(hat_bundle, query_dps).values[0][0]
            results[hat] = score
    return results
