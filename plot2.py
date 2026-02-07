#!/usr/bin/env python3
"""
Dual Y-axis plot script for random walk strategy comparison
Reads plot.txt and generates a graph with TWO y-axes:
  - Left axis: Resilience Gain (RG)
  - Right axis: Coverage (0-1 normalized)
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


def create_dual_axis_plot(config: Dict, series_data: Dict[str, List[Tuple[float, float, float]]]):
    """
    Create plot with dual y-axes:
      - Left axis: First series (RG - Resilience Gain)
      - Right axis: Second series (Coverage)
    """
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Convert series_data to list to access by index
    series_list = list(series_data.items())

    if len(series_list) < 2:
        print("⚠️  Warning: Need at least 2 series for dual-axis plot!")
        return None

    # First series (RG) on left axis
    rg_name, rg_data = series_list[0]
    rg_x = [point[0] for point in rg_data]
    rg_y = [point[1] for point in rg_data]
    rg_ci = [point[2] for point in rg_data]

    color1 = '#1f77b4'  # Blue for RG
    ax1.errorbar(
        rg_x, rg_y, yerr=rg_ci,
        label=rg_name,
        marker='o',
        color=color1,
        capsize=5,
        capthick=2,
        linewidth=2.5,
        markersize=8,
        linestyle='-',
        alpha=0.85
    )

    # Set left y-axis (RG)
    ax1.set_xlabel(config.get('xlabel', 'ステップ'), fontsize=14, fontweight='bold')
    ax1.set_ylabel(config.get('ylabel', 'レジリエンスゲイン'),
                   fontsize=14, fontweight='bold', color=color1)
    ax1.tick_params(axis='y', labelcolor=color1, labelsize=11)

    # Set left y-axis limits and ticks
    if 'ymax' in config:
        ax1.set_ylim(0, config['ymax'])
    if 'ygap' in config and 'ymax' in config:
        y_ticks = range(0, int(config['ymax']) + 1, int(config['ygap']))
        ax1.set_yticks(y_ticks)

    # Add ytarget line if specified (for RG)
    if 'ytarget' in config:
        ax1.axhline(
            y=config['ytarget'],
            color='red',
            linestyle='--',
            linewidth=2,
            alpha=0.6,
            label=f"Target: {config['ytarget']}"
        )

    # Create second y-axis (right) for Coverage
    ax2 = ax1.twinx()

    # Second series (Coverage) on right axis
    cov_name, cov_data = series_list[1]
    cov_x = [point[0] for point in cov_data]
    cov_y = [point[1] for point in cov_data]
    cov_ci = [point[2] for point in cov_data]

    color2 = '#ff7f0e'  # Orange for Coverage
    ax2.errorbar(
        cov_x, cov_y, yerr=cov_ci,
        label=cov_name,
        marker='s',
        color=color2,
        capsize=5,
        capthick=2,
        linewidth=2.5,
        markersize=8,
        linestyle='-',
        alpha=0.85
    )

    # Set right y-axis (Coverage)
    ax2.set_ylabel('カバレッジ', fontsize=14, fontweight='bold', color=color2)
    ax2.tick_params(axis='y', labelcolor=color2, labelsize=11)
    ax2.set_ylim(0, 1.0)  # Coverage is normalized to 0-1
    ax2.set_yticks([i * 0.1 for i in range(11)])  # 0.0, 0.1, ..., 1.0

    # Set x-axis limits and ticks
    if 'xmax' in config:
        ax1.set_xlim(0, config['xmax'])
    if 'xgap' in config and 'xmax' in config:
        x_ticks = range(0, int(config['xmax']) + 1, int(config['xgap']))
        ax1.set_xticks(x_ticks)

    # Grid (only on ax1 to avoid overlap)
    ax1.grid(True, alpha=0.3, linestyle='--', linewidth=1)

    # Combine legends from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               fontsize=12, framealpha=0.95, loc='upper left')

    # Styling
    ax1.spines['top'].set_visible(False)
    ax1.spines['left'].set_color(color1)
    ax1.spines['left'].set_linewidth(2)
    ax2.spines['right'].set_color(color2)
    ax2.spines['right'].set_linewidth(2)

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

        print(f"📊 Found {len(series_data)} series: {list(series_data.keys())}")

        # Create the dual-axis plot
        fig = create_dual_axis_plot(config, series_data)

        if fig is None:
            sys.exit(1)

        # Save and show
        output_file = input_file.replace('.txt', '_dual.png')
        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✨ Dual-axis plot saved to: {output_file}")

        plt.show()

    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
