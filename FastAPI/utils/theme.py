import matplotlib.pyplot as plt


def apply_corporate_theme():
    """Apply corporate styling to all plots"""
    plt.style.use('seaborn-v0_8-whitegrid')

    # Corporate colors
    primary_blue = "#003366"    # Deep Blue
    secondary_blue = "#0072CE"  # Light Blue

    # Extended palette with more variety
    corporate_palette = [
        primary_blue,
        secondary_blue,
        "#4A99D8",  # Lighter blue variant
        "#001F3D",  # Darker blue variant
        "#7FB2E5",  # Very light blue
        "#00509E", # Medium blue
        "#B3D7FF", # Very pale blue
        "#5F9BD1", # Sky blue
        "#2A4E76", # Navy blue
        "#A4C8E1", # Pastel blue
        "#1F5C9D", # Royal blue
        "#6CA2D4"  # Steel blue
    ]

    # Apply common styling
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False

    return corporate_palette