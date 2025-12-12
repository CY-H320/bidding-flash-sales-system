"""
Analyze bid request logs and generate visualizations.

This script reads the bid_requests.csv log file and generates:
1. Requests per second line chart
2. Bid price over time chart
3. Success rate over time chart
4. Response time distribution

Usage:
    python analyze_bid_logs.py results_<timestamp>
    python analyze_bid_logs.py results_20231211_120000
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def analyze_bid_logs(results_dir):
    """Analyze bid logs and generate charts."""

    results_path = Path(results_dir)
    bid_log_file = results_path / "bid_requests.csv"

    if not bid_log_file.exists():
        print(f"❌ Error: {bid_log_file} not found")
        print("   Make sure you run the test first to generate logs")
        return

    print(f"📊 Reading bid logs from: {bid_log_file}")

    # Read CSV
    df = pd.read_csv(bid_log_file)

    print(f"✅ Loaded {len(df)} bid requests")
    print(
        f"   Time range: {df['elapsed_seconds'].min():.1f}s - {df['elapsed_seconds'].max():.1f}s"
    )
    print(f"   Success rate: {df['success'].sum() / len(df) * 100:.1f}%")

    # Create output directory
    output_dir = results_path / "analysis"
    output_dir.mkdir(exist_ok=True)

    # Set style
    plt.style.use("seaborn-v0_8-darkgrid")

    # 1. Requests per second chart
    print("\n📈 Generating requests per second chart...")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Group by elapsed seconds (rounded to nearest second)
    df["second"] = df["elapsed_seconds"].round(0).astype(int)
    requests_per_second = df.groupby("second").size()

    ax.plot(
        requests_per_second.index,
        requests_per_second.values,
        linewidth=2,
        color="#2E86DE",
        marker="o",
        markersize=3,
    )
    ax.fill_between(
        requests_per_second.index,
        requests_per_second.values,
        alpha=0.3,
        color="#2E86DE",
    )

    ax.set_xlabel("Elapsed Time (seconds)", fontsize=12)
    ax.set_ylabel("Bid Requests per Second", fontsize=12)
    ax.set_title("Bid Request Rate Over Time", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)

    # Add statistics
    avg_rps = requests_per_second.mean()
    max_rps = requests_per_second.max()
    ax.text(
        0.02,
        0.98,
        f"Avg: {avg_rps:.1f} req/s\nMax: {max_rps:.0f} req/s",
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    plt.tight_layout()
    chart_file = output_dir / "requests_per_second.png"
    plt.savefig(chart_file, dpi=300, bbox_inches="tight")
    print(f"   ✅ Saved to: {chart_file}")
    plt.close()

    # 2. Bid price over time chart
    print("📈 Generating bid price over time chart...")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Sample data if too many points
    if len(df) > 1000:
        sample_df = df.sample(min(1000, len(df)))
    else:
        sample_df = df

    ax.scatter(
        sample_df["elapsed_seconds"],
        sample_df["bid_price"],
        alpha=0.5,
        s=10,
        color="#10AC84",
    )

    # Add trend line
    z = np.polyfit(df["elapsed_seconds"], df["bid_price"], 1)
    p = np.poly1d(z)
    ax.plot(
        df["elapsed_seconds"],
        p(df["elapsed_seconds"]),
        "r--",
        linewidth=2,
        label=f"Trend: +${z[0]:.2f}/sec",
    )

    ax.set_xlabel("Elapsed Time (seconds)", fontsize=12)
    ax.set_ylabel("Bid Price ($)", fontsize=12)
    ax.set_title("Bid Price Increase Over Time", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    chart_file = output_dir / "bid_price_over_time.png"
    plt.savefig(chart_file, dpi=300, bbox_inches="tight")
    print(f"   ✅ Saved to: {chart_file}")
    plt.close()

    # 3. Success rate over time (5-second intervals)
    print("📈 Generating success rate over time chart...")
    fig, ax = plt.subplots(figsize=(12, 6))

    df["interval"] = (df["elapsed_seconds"] // 5 * 5).astype(int)
    success_rate = df.groupby("interval")["success"].mean() * 100

    ax.plot(
        success_rate.index,
        success_rate.values,
        linewidth=2,
        color="#EE5A6F",
        marker="s",
        markersize=5,
    )
    ax.fill_between(success_rate.index, success_rate.values, alpha=0.3, color="#EE5A6F")

    ax.set_xlabel("Elapsed Time (seconds)", fontsize=12)
    ax.set_ylabel("Success Rate (%)", fontsize=12)
    ax.set_title(
        "Bid Success Rate Over Time (5-second intervals)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_ylim([0, 105])
    ax.grid(True, alpha=0.3)

    # Add horizontal line at 100%
    ax.axhline(y=100, color="gray", linestyle="--", alpha=0.5, linewidth=1)

    plt.tight_layout()
    chart_file = output_dir / "success_rate_over_time.png"
    plt.savefig(chart_file, dpi=300, bbox_inches="tight")
    print(f"   ✅ Saved to: {chart_file}")
    plt.close()

    # 4. Response time distribution
    print("📈 Generating response time distribution chart...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    ax1.hist(
        df["response_time_ms"], bins=50, color="#FFA502", alpha=0.7, edgecolor="black"
    )
    ax1.set_xlabel("Response Time (ms)", fontsize=12)
    ax1.set_ylabel("Frequency", fontsize=12)
    ax1.set_title("Response Time Distribution", fontsize=13, fontweight="bold")
    ax1.grid(True, alpha=0.3, axis="y")

    # Add statistics
    median_rt = df["response_time_ms"].median()
    p95_rt = df["response_time_ms"].quantile(0.95)
    p99_rt = df["response_time_ms"].quantile(0.99)

    ax1.axvline(
        median_rt,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_rt:.0f}ms",
    )
    ax1.axvline(
        p95_rt,
        color="orange",
        linestyle="--",
        linewidth=2,
        label=f"P95: {p95_rt:.0f}ms",
    )
    ax1.legend()

    # Box plot
    ax2.boxplot(
        [df["response_time_ms"]],
        vert=True,
        patch_artist=True,
        boxprops=dict(facecolor="#FFA502", alpha=0.7),
        medianprops=dict(color="red", linewidth=2),
        whiskerprops=dict(linewidth=1.5),
        capprops=dict(linewidth=1.5),
    )
    ax2.set_ylabel("Response Time (ms)", fontsize=12)
    ax2.set_title("Response Time Box Plot", fontsize=13, fontweight="bold")
    ax2.set_xticklabels(["All Requests"])
    ax2.grid(True, alpha=0.3, axis="y")

    # Add text with stats
    stats_text = f"Median: {median_rt:.1f}ms\nP95: {p95_rt:.1f}ms\nP99: {p99_rt:.1f}ms"
    ax2.text(
        0.98,
        0.98,
        stats_text,
        transform=ax2.transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    plt.tight_layout()
    chart_file = output_dir / "response_time_distribution.png"
    plt.savefig(chart_file, dpi=300, bbox_inches="tight")
    print(f"   ✅ Saved to: {chart_file}")
    plt.close()

    # 5. Combined dashboard
    print("📈 Generating combined dashboard...")
    fig = plt.figure(figsize=(16, 10))

    # Create grid
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Requests per second
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(
        requests_per_second.index,
        requests_per_second.values,
        linewidth=2,
        color="#2E86DE",
        marker="o",
        markersize=3,
    )
    ax1.fill_between(
        requests_per_second.index,
        requests_per_second.values,
        alpha=0.3,
        color="#2E86DE",
    )
    ax1.set_xlabel("Elapsed Time (seconds)")
    ax1.set_ylabel("Requests/sec")
    ax1.set_title("Bid Request Rate Over Time", fontweight="bold")
    ax1.grid(True, alpha=0.3)
    ax1.text(
        0.02,
        0.98,
        f"Avg: {avg_rps:.1f} req/s\nMax: {max_rps:.0f} req/s",
        transform=ax1.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # Bid price
    ax2 = fig.add_subplot(gs[1, 0])
    sample_df = df.sample(min(500, len(df)))
    ax2.scatter(
        sample_df["elapsed_seconds"],
        sample_df["bid_price"],
        alpha=0.5,
        s=10,
        color="#10AC84",
    )
    z = np.polyfit(df["elapsed_seconds"], df["bid_price"], 1)
    p = np.poly1d(z)
    ax2.plot(
        df["elapsed_seconds"],
        p(df["elapsed_seconds"]),
        "r--",
        linewidth=2,
        label=f"Trend: +${z[0]:.2f}/sec",
    )
    ax2.set_xlabel("Elapsed Time (seconds)")
    ax2.set_ylabel("Bid Price ($)")
    ax2.set_title("Bid Price Increase Over Time", fontweight="bold")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Success rate
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(
        success_rate.index,
        success_rate.values,
        linewidth=2,
        color="#EE5A6F",
        marker="s",
        markersize=5,
    )
    ax3.fill_between(
        success_rate.index, success_rate.values, alpha=0.3, color="#EE5A6F"
    )
    ax3.set_xlabel("Elapsed Time (seconds)")
    ax3.set_ylabel("Success Rate (%)")
    ax3.set_title("Success Rate (5s intervals)", fontweight="bold")
    ax3.set_ylim([0, 105])
    ax3.axhline(y=100, color="gray", linestyle="--", alpha=0.5)
    ax3.grid(True, alpha=0.3)

    # Response time
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.hist(
        df["response_time_ms"], bins=50, color="#FFA502", alpha=0.7, edgecolor="black"
    )
    ax4.axvline(
        median_rt,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_rt:.0f}ms",
    )
    ax4.set_xlabel("Response Time (ms)")
    ax4.set_ylabel("Frequency")
    ax4.set_title("Response Time Distribution", fontweight="bold")
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis="y")

    # Summary stats
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.axis("off")

    summary_stats = f"""
    📊 TEST SUMMARY
    
    Total Requests:     {len(df):,}
    Test Duration:      {df["elapsed_seconds"].max():.1f}s
    
    Request Rate:
      • Average:        {avg_rps:.1f} req/s
      • Maximum:        {max_rps:.0f} req/s
    
    Bid Price:
      • Starting:       ${df["bid_price"].iloc[0]:.2f}
      • Ending:         ${df["bid_price"].iloc[-1]:.2f}
      • Increase Rate:  ${z[0]:.2f}/sec
    
    Success Rate:       {df["success"].sum() / len(df) * 100:.1f}%
    
    Response Time:
      • Median:         {median_rt:.1f}ms
      • P95:            {p95_rt:.1f}ms
      • P99:            {p99_rt:.1f}ms
    """

    ax5.text(
        0.1,
        0.5,
        summary_stats,
        fontsize=11,
        verticalalignment="center",
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="#F0F0F0", alpha=0.8),
    )

    plt.suptitle(
        "Bid Load Test Analysis Dashboard", fontsize=16, fontweight="bold", y=0.995
    )

    chart_file = output_dir / "dashboard.png"
    plt.savefig(chart_file, dpi=300, bbox_inches="tight")
    print(f"   ✅ Saved to: {chart_file}")
    plt.close()

    print("\n" + "=" * 70)
    print("✅ Analysis Complete!")
    print("=" * 70)
    print(f"All charts saved to: {output_dir}")
    print("\nGenerated files:")
    print("  1. requests_per_second.png")
    print("  2. bid_price_over_time.png")
    print("  3. success_rate_over_time.png")
    print("  4. response_time_distribution.png")
    print("  5. dashboard.png (combined view)")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_bid_logs.py <results_directory>")
        print("Example: python analyze_bid_logs.py results_20231211_120000")
        sys.exit(1)

    results_dir = sys.argv[1]
    analyze_bid_logs(results_dir)
