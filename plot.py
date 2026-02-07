#!/usr/bin/env python3
"""
Plot script for random walk strategy comparison
Reads plot.txt and generates a graph with error bars
"""

import matplotlib.pyplot as plt
import matplotlib
from typing import Dict, List, Tuple
import sys

# Set Japanese font support
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
matplotlib.rcParams['axes.unicode_minus'] = False


def parse_plot_file(filename: str) -> Tuple[Dict, Dict[str, List[Tuple[float, float, float]]]]:
    """
    Parse plot.txt file to extract configuration and data series

    Returns:
        config: Dictionary with xlabel, ylabel, xmax, ymax, xgap, ygap, ytarget
        series_data: Dictionary mapping series name to list of (x, y, ci) tuples
    """
    config = {}
    series_data = {}
    current_series = None

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Parse config lines (key: value)
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Store config values
                if key in ['xlabel', 'ylabel']:
                    config[key] = value
                else:
                    try:
                        config[key] = float(value)
                    except ValueError:
                        config[key] = value

            # Parse series header (# SeriesName)
            elif line.startswith('#'):
                current_series = line[1:].strip()
                series_data[current_series] = []

            # Parse data lines (x y ci)
            elif current_series is not None:
                parts = line.split()
                if len(parts) == 3:
                    try:
                        x = float(parts[0])
                        y = float(parts[1])
                        ci = float(parts[2])
                        series_data[current_series].append((x, y, ci))
                    except ValueError:
                        continue

    return config, series_data


def create_plot(config: Dict, series_data: Dict[str, List[Tuple[float, float, float]]]):
    """
    Create and display the plot with error bars
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot each series with error bars
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    markers = ['o', 's', '^', 'D', 'v', '<']

    for idx, (series_name, data) in enumerate(series_data.items()):
        if not data:
            continue

        x_vals = [point[0] for point in data]
        y_vals = [point[1] for point in data]
        ci_vals = [point[2] for point in data]

        ax.errorbar(
            x_vals, y_vals, yerr=ci_vals,
            label=series_name,
            marker=markers[idx % len(markers)],
            color=colors[idx % len(colors)],
            capsize=5,
            capthick=2,
            linewidth=2,
            markersize=8,
            linestyle='-',
            alpha=0.8
        )

    # Set labels
    if 'xlabel' in config:
        ax.set_xlabel(config['xlabel'], fontsize=14, fontweight='bold')
    if 'ylabel' in config:
        ax.set_ylabel(config['ylabel'], fontsize=14, fontweight='bold')

    # Set axis limits
    if 'xmax' in config:
        ax.set_xlim(0, config['xmax'])
    if 'ymax' in config:
        ax.set_ylim(0, config['ymax'])

    # Set grid with specified intervals
    if 'xgap' in config and 'xmax' in config:
        x_ticks = range(0, int(config['xmax']) + 1, int(config['xgap']))
        ax.set_xticks(x_ticks)

    if 'ygap' in config and 'ymax' in config:
        y_ticks = range(0, int(config['ymax']) + 1, int(config['ygap']))
        ax.set_yticks(y_ticks)

    # Add ytarget line if specified
    if 'ytarget' in config:
        ax.axhline(
            y=config['ytarget'],
            color='red',
            linestyle='-',
            linewidth=2,
            alpha=0.5,
            label=f"Target: {config['ytarget']}"
        )

    # Styling
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, framealpha=0.9, loc='best')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    return fig


def main():
    # Default input file
    input_file = 'plot.txt'

    # Allow command line argument for input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    try:
        # Parse the input file
        config, series_data = parse_plot_file(input_file)

        # Create the plot
        fig = create_plot(config, series_data)

        # Save and show
        output_file = input_file.replace('.txt', '.png')
        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✨ Plot saved to: {output_file}")

        plt.show()

    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
