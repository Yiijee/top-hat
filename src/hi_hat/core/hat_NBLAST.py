import navis


def hat_nblast(
    query_path: str,
    target_list: list[str],
    th: int,
    loader: any,
    progress_wrapper=None,
) -> dict:
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
