# src/top_hat/utils/plotter.py

from pathlib import Path


def plot_tracts_placeholder(
    active_hemilineages: list[dict[str, any]], output_path: Path
):
    """
    A placeholder function to save information for plotting tracts.

    In the future, this function will generate and save a plot.
    """
    print("--- Plotting Tracts (Placeholder) ---")
    print(f"Output path: {output_path}")
    print("Active hemilineages to plot:")
    for item in active_hemilineages:
        print(f"- Name: {item['name']}, Color: {item['color']}")
    print("------------------------------------")
    # In the future, replace this with actual plotting code (e.g., using matplotlib)

    # For now, we can just save the info to a text file to show it works.
    with open(output_path, "w") as f:
        f.write("Tract Plotting Information:\n")
        for item in active_hemilineages:
            f.write(f"Name: {item['name']}, Color: {item['color']}\n")
