from pathlib import Path

import matplotlib.pyplot as plt
import navis


def plot_tracts(
    active_hemilineages: dict[str, str],
    output_path: Path,
    loader: any,
    plot_symmetry: bool = False,
    progress_wrapper: any = None,
):
    """Plots hemilineage tracts and saves the figure to a file.

    This function generates a 2D plot of specified hemilineage tracts,
    optionally including their symmetric counterparts, overlaid on a brain mesh.

    Args:
        active_hemilineages (dict[str, str]): A dictionary where keys are
            hemilineage names and values are their corresponding hex color codes.
        output_path (Path): The file path where the output plot image will be saved.
        loader (any): An instance of a data loader class that provides access
            to hemilineage data and brain meshes.
        plot_symmetry (bool, optional): If True, plots the symmetrized version
            of the tracts. Defaults to False.
        progress_wrapper (any, optional): A wrapper function (like tqdm) to
            provide progress updates for the plotting process. Defaults to None.
    """
    iterable = active_hemilineages.items()
    JRC2018U_mesh = loader.get_JRC2018U_mesh()

    print("----------- Plotting Tracts---------")
    print(f"Output path: {output_path}")
    print("Active hemilineages to plot:")
    for key, value in iterable:
        print(f"- Name: {key}, Color: {value}")
    print("------------------------------------")

    if progress_wrapper:
        iterable = progress_wrapper(iterable, desc="Plotting tracts:")
    tract_nl = []
    color_list = []
    for hemilineage, color in iterable:
        if plot_symmetry:
            tract = loader._get_data(
                hemilineage, "_hat_bundles_sym.pkl", "pkl"
            )
        else:
            tract = loader._get_data(hemilineage, "_hat_bundles.pkl", "pkl")
        tract = navis.make_dotprops(tract, k=100, resample=0.5)
        tract = navis.drop_fluff(tract, n_largest=2)
        tract_nl.append(tract.to_skeleton(1))
        color_list.append(color)
    tract_nl = navis.NeuronList(tract_nl)
    fig, ax = navis.plot2d(
        [tract_nl, JRC2018U_mesh],
        color=color_list,
        alpha=0.7,
        method="2d",
        view=("x", "-y"),
        linewidth=0.2,
    )
    ax.axis("off")
    plt.savefig(output_path, dpi=400, bbox_inches="tight")
