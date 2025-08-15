import random


def generate_random_hex_color() -> str:
    """
    Generates a random 6-digit hex color code.

    Returns:
        str: A hex color string, e.g., '#RRGGBB'.
    """
    return f"#{random.randint(0, 0xFFFFFF):06x}"


if __name__ == "__main__":
    # Generate and print 5 random hex colors
    for _ in range(5):
        print(generate_random_hex_color())
