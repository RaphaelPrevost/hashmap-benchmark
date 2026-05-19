#!/usr/bin/env python3

import argparse
import json
import shlex
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

import matplotlib.pyplot as plt
import pandas as pd
import yaml
from typing import Optional

ROOT = Path(__file__).resolve().parent
HASHMAP_DIR = ROOT / "hashmap"
DEFAULT_OUTPUT_DIR = ROOT / "docs"

MODES = ["insert", "update", "retrieve", "miss"]
SIZES = [
    (5_000, 100),
    (8_000, 100),
    (10_000, 100),
    (20_000, 100),
    (50_000, 50),
    (80_000, 50),
    (100_000, 50),
    (200_000, 50),
    (300_000, 30),
    (400_000, 30),
    (500_000, 10),
    (600_000, 20),
    (800_000, 10),
    (1_000_000, 10),
    (1_500_000, 10),
    (2_000_000, 10),
    (3_000_000, 5),
    (5_000_000, 5),
    (8_000_000, 5),
    (10_000_000, 5),
]
ZOOM_MAX_KEYS = 1_000_000
EXPECTED_KEYS = {count for count, _ in SIZES}
EXPECTED_TESTS = set(MODES)


# ---------------------------------------------------------------------------
# Config/source/build helpers
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def github_raw_url(repo: str, ref: str, relpath: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{relpath}"


def download_file(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response:
        data = response.read()
    dst.write_bytes(data)


def process_implementation(impl_dir: Path, config: dict) -> None:
    source = config.get("source", {})
    if source.get("type") == "github-raw" and "files" in source:
        repo = source["repo"]
        ref = source["ref"]
        files = source.get("files", [])

        print(f"==> {impl_dir.name}")
        for relpath in files:
            url = github_raw_url(repo, ref, relpath)
            dst = impl_dir / "src" / relpath
            download_file(url, dst)
            print(f"  downloaded {relpath}")
    else:
        print(f"==> {impl_dir.name} [no source download needed]")


def _require_field(mapping: dict, key: str, ctx: str):
    value = mapping.get(key)
    if value is None:
        raise ValueError(f"{ctx}: missing required field '{key}'")
    return value


def _as_list(value, ctx: str):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{ctx}: expected a list")
    return value


def _resolve_impl_path(impl_dir: Path, relpath: str) -> Path:
    return (impl_dir / relpath).resolve()


def _validate_existing_files(impl_dir: Path, paths: list[str], ctx: str) -> None:
    missing = []
    for relpath in paths:
        path = _resolve_impl_path(impl_dir, relpath)
        if not path.is_file():
            missing.append(relpath)
    if missing:
        raise FileNotFoundError(
            f"{ctx}: missing files:\n  " + "\n  ".join(missing)
        )


def _print_command(prefix: str, cmd: list[str]) -> None:
    print(prefix + shlex.join(cmd))


def build_cc(impl_dir: Path, config: dict) -> None:
    build = config.get("build", {})
    ctx = f"{impl_dir.name}.build"

    compiler = _require_field(build, "compiler", ctx)
    output = _require_field(build, "output", ctx)
    sources = _as_list(_require_field(build, "sources", ctx), f"{ctx}.sources")
    cflags = _as_list(build.get("cflags"), f"{ctx}.cflags")
    cppflags = _as_list(build.get("cppflags"), f"{ctx}.cppflags")
    include_dirs = _as_list(build.get("include_dirs"), f"{ctx}.include_dirs")
    ldflags = _as_list(build.get("ldflags"), f"{ctx}.ldflags")
    libs = _as_list(build.get("libs"), f"{ctx}.libs")

    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise RuntimeError(f"{ctx}: compiler not found in PATH: {compiler}")

    _validate_existing_files(impl_dir, sources, f"{ctx}.sources")

    for inc in include_dirs:
        inc_path = _resolve_impl_path(impl_dir, inc)
        if not inc_path.exists():
            raise FileNotFoundError(f"{ctx}.include_dirs: missing directory: {inc}")

    cmd = [compiler]
    cmd += cppflags
    cmd += cflags

    for inc in include_dirs:
        cmd += ["-I", inc]

    cmd += sources
    cmd += ldflags
    cmd += libs
    cmd += ["-o", output]

    print(f"==> building {impl_dir.name} [cc]")
    _print_command("    ", cmd)

    subprocess.run(cmd, cwd=impl_dir, check=True)


def build_cmake(impl_dir: Path, config: dict) -> None:
    build = config.get("build", {})
    ctx = f"{impl_dir.name}.build"

    build_dir = impl_dir / build.get("build_dir", "build")
    configure_args = _as_list(build.get("configure_args"), f"{ctx}.configure_args")
    build_args = _as_list(build.get("build_args"), f"{ctx}.build_args")
    output_rel = _require_field(build, "output", ctx)
    output_path = impl_dir / output_rel

    configure_cmd = ["cmake", "-S", str(impl_dir), "-B", str(build_dir)] + configure_args
    print(f"==> configuring {impl_dir.name} [cmake]")
    _print_command("    ", configure_cmd)
    subprocess.run(configure_cmd, check=True)

    build_cmd = ["cmake", "--build", str(build_dir)] + build_args
    print(f"==> building {impl_dir.name} [cmake]")
    _print_command("    ", build_cmd)
    subprocess.run(build_cmd, check=True)

    if not output_path.is_file():
        raise FileNotFoundError(f"{ctx}: expected output binary not found: {output_rel}")


def build_cargo(impl_dir: Path, config: dict) -> None:
    ctx = f"{impl_dir.name}.build"

    if shutil.which("cargo") is None:
        raise RuntimeError(f"{ctx}: cargo not found in PATH")

    src_bench = impl_dir / "benchmark.rs"
    dst_main = impl_dir / "src" / "main.rs"

    dst_main.parent.mkdir(exist_ok=True)
    shutil.copy2(src_bench, dst_main)

    cargo_cmd = ["cargo", "build", "--release"]
    print(f"==> building {impl_dir.name} [cargo]")
    _print_command("    ", cargo_cmd)
    subprocess.run(cargo_cmd, cwd=impl_dir, check=True)

    src_exe = impl_dir / "target" / "release" / "hashbench"
    dst_exe = impl_dir / "hashbench"

    if src_exe.is_file():
        shutil.copy2(src_exe, dst_exe)
        print(f"  copied {src_exe} -> {dst_exe}")
    else:
        raise FileNotFoundError(f"{ctx}: cargo binary not built: {src_exe}")


def build_implementation(impl_dir: Path, config: dict) -> None:
    build = config.get("build", {})
    ctx = f"{impl_dir.name}.build"
    system = _require_field(build, "system", ctx)

    if system == "none":
        return

    builders = {
        "cc": build_cc,
        "cmake": build_cmake,
        "cargo": build_cargo,
    }

    builder = builders.get(system)
    if builder is None:
        supported = ", ".join(sorted(builders))
        raise ValueError(
            f"{ctx}: unsupported build.system '{system}' "
            f"(supported: {supported})"
        )

    builder(impl_dir, config)


# ---------------------------------------------------------------------------
# Benchmark execution
# ---------------------------------------------------------------------------


def _exe_path(impl_dir: Path, relpath: str) -> Path:
    path = (impl_dir / relpath).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{impl_dir.name}: executable not found: {relpath}")
    return path


def smoke_test(impl_dir: Path) -> None:
    exe = _exe_path(impl_dir, "hashbench")
    cmd = [str(exe), "retrieve", "1000"]
    print(f"==> smoke test {impl_dir.name}")
    _print_command("    ", cmd)
    subprocess.run(cmd, cwd=impl_dir, check=True)


def hyperfine_benchmark(impl_dir: Path) -> None:
    if shutil.which("hyperfine") is None:
        raise RuntimeError("hyperfine not found in PATH")

    exe = _exe_path(impl_dir, "hashbench")
    results_dir = impl_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    for mode in MODES:
        for count, runs in SIZES:
            cmdline = [str(exe), mode, str(count)]
            json_path = results_dir / f"{mode}-{count}.json"
            hcmd = [
                "hyperfine",
                "--warmup", "1",
                "--runs", str(runs),
                "-N",
                "--export-json", str(json_path),
                shlex.join(cmdline),
            ]
            print(f"==> benchmark {impl_dir.name}: {mode} {count} ({runs} runs)")
            _print_command("    ", hcmd)
            subprocess.run(hcmd, cwd=impl_dir, check=True)


def discover_implementations(hashmap_dir: Path) -> list[Path]:
    impls = []
    for child in sorted(hashmap_dir.iterdir()):
        if child.is_dir() and (child / "config.yml").is_file():
            impls.append(child)
    return impls


def select_implementations(hashmap_dir: Path, names: list[str]) -> list[Path]:
    impls = discover_implementations(hashmap_dir)
    by_name = {impl.name: impl for impl in impls}

    if not names:
        return impls

    selected = []
    missing = []
    for name in names:
        impl = by_name.get(name)
        if impl is None:
            missing.append(name)
        else:
            selected.append(impl)

    if missing:
        available = ", ".join(sorted(by_name))
        raise SystemExit(
            "unknown implementation(s): " + ", ".join(missing) +
            f"\navailable implementations: {available}"
        )

    return selected


def refresh_implementation(impl_dir: Path) -> None:
    config = load_config(impl_dir / "config.yml")
    process_implementation(impl_dir, config)
    build_implementation(impl_dir, config)
    smoke_test(impl_dir)
    hyperfine_benchmark(impl_dir)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def load_display_name(impl_dir: Path) -> str:
    config_path = impl_dir / "config.yml"
    if not config_path.exists():
        return impl_dir.name

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    return config.get("display_name", impl_dir.name)


def collect_benchmark_rows(root: Path) -> pd.DataFrame:
    rows = []
    skipped = []

    for result_path in sorted(root.glob("hashmap/*/results/*.json")):
        impl_dir = result_path.parent.parent
        impl = impl_dir.name
        display_name = load_display_name(impl_dir)

        stem = result_path.stem  # e.g. insert-10000
        if "-" not in stem:
            skipped.append(result_path)
            continue

        test, keys_str = stem.split("-", 1)
        try:
            keys = int(keys_str)
        except ValueError:
            skipped.append(result_path)
            continue

        if test not in EXPECTED_TESTS or keys not in EXPECTED_KEYS:
            skipped.append(result_path)
            continue

        with result_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for result in data.get("results", []):
            times = result.get("times", [])
            exit_codes = result.get("exit_codes", [])
            ok_runs = sum(1 for code in exit_codes if code == 0)

            rows.append({
                "impl": impl,
                "display_name": display_name,
                "test": test,
                "keys": keys,
                "mean_ms": result["mean"] * 1000.0,
                "median_ms": result["median"] * 1000.0,
                "stddev_ms": result["stddev"] * 1000.0,
                "min_ms": result["min"] * 1000.0,
                "max_ms": result["max"] * 1000.0,
                "runs": len(times),
                "ok_runs": ok_runs,
                "success_rate": (ok_runs / len(exit_codes) * 100.0) if exit_codes else 100.0,
            })

    if skipped:
        print(f"==> ignored {len(skipped)} stale/unexpected result file(s)")

    if not rows:
        return pd.DataFrame(columns=[
            "impl", "display_name", "test", "keys",
            "mean_ms", "median_ms", "stddev_ms",
            "min_ms", "max_ms", "runs", "ok_runs", "success_rate"
        ])

    return pd.DataFrame(rows)


def aggregate_rows(df: pd.DataFrame, metric: str = "median_ms") -> pd.DataFrame:
    if df.empty:
        return df.copy()

    agg = (
        df.groupby(["test", "impl", "display_name", "keys"], as_index=False)
          .agg(
              value=(metric, "mean"),
              mean_ms=("mean_ms", "mean"),
              median_ms=("median_ms", "mean"),
              stddev_ms=("stddev_ms", "mean"),
              min_ms=("min_ms", "min"),
              max_ms=("max_ms", "max"),
              runs=("runs", "sum"),
              success_rate=("success_rate", "mean"),
          )
          .sort_values(["test", "keys", "display_name"])
    )
    return agg


def make_test_table(df_test: pd.DataFrame) -> pd.DataFrame:
    table = (
        df_test.pivot(index="keys", columns="display_name", values="value")
               .sort_index()
    )
    return table.round(3)


def _style_for_series(display_name: str, idx: int) -> tuple[str, str, float]:
    style_cycle = ['o-', 's-', '^-', 'D-', 'x-', 'v-', 'p-', '*-', 'h-', '<-', '>-']
    color_cycle = ['#d62728', '#1f77b4', '#2ca02c', '#ff7f0e', '#bbbbbb',
                   '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#7f7f7f']
    name = display_name.lower()
    linewidth = 2.2 if "askl" in name else 1.1
    return style_cycle[idx % len(style_cycle)], color_cycle[idx % len(color_cycle)], linewidth


def plot_test_chart(
    df_test: pd.DataFrame,
    test_name: str,
    output_dir: Path,
    *,
    filename: Optional[str] = None,
    title_suffix: str = "",
    zoomed: bool = False,
) -> Path:
    if df_test.empty:
        raise ValueError(f"no rows available for {test_name} chart")

    series = []
    for idx, (display_name, sub) in enumerate(df_test.groupby("display_name")):
        sub = sub.sort_values("keys")
        style, color, linewidth = _style_for_series(display_name, idx)
        series.append({
            "display_name": display_name,
            "keys": sub["keys"].tolist(),
            "values": sub["value"].tolist(),
            "style": style,
            "color": color,
            "linewidth": linewidth,
        })

    fig, ax = plt.subplots(figsize=(12, 7))

    for s in series:
        ax.loglog(
            s["keys"],
            s["values"],
            s["style"],
            linewidth=s["linewidth"],
            markersize=3,
            label=s["display_name"],
            color=s["color"],
        )

    range_label = "≤ 1M keys" if zoomed else "full range"
    ax.set_xlabel('Number of Keys (log scale)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Time (ms, log scale)', fontsize=12, fontweight='bold')
    ax.set_title(
        f'Hash Table Performance Comparison: {test_name.title()} ({range_label}){title_suffix}',
        fontsize=14,
        fontweight='bold',
        pad=20,
    )
    ax.text(
        0.5,
        1.02,
        f'{test_name.title()} benchmark',
        transform=ax.transAxes,
        ha='center',
        fontsize=10,
        style='italic',
    )

    ax.grid(True, which='both', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.grid(True, which='minor', linestyle=':', linewidth=0.3, alpha=0.2)

    ax.legend(loc='upper left', fontsize=11, frameon=True, shadow=True)
    ax.tick_params(axis='both', which='major', labelsize=10)

    x_min = min(min(s["keys"]) for s in series)
    x_max = max(max(s["keys"]) for s in series)
    y_min = min(min(s["values"]) for s in series)
    y_max = max(max(s["values"]) for s in series)

    ax.set_xlim(x_min, x_max * 1.25)
    ax.set_ylim(max(0.1, y_min * 0.8), y_max * 1.5)

    plt.tight_layout()

    output_path = output_dir / (filename or f"{test_name}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    return output_path


def _append_test_section(md_parts: list[str], title: str, df_test: pd.DataFrame, chart_path: Path) -> None:
    table = make_test_table(df_test)
    md_parts.append(f"### {title}")
    md_parts.append("")
    md_parts.append(f"![{title} chart]({chart_path.name})")
    md_parts.append("")
    md_parts.append(table.to_markdown())
    md_parts.append("")


def build_benchmark_report(root: Path, output_dir: Path, metric: str = "median_ms") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")

    raw_df = collect_benchmark_rows(root)
    if raw_df.empty:
        raise RuntimeError(f"No benchmark JSON files found under {root / 'hashmap/*/results/*.json'}")

    agg_df = aggregate_rows(raw_df, metric=metric)
    zoom_df = agg_df[agg_df["keys"] <= ZOOM_MAX_KEYS].copy()

    agg_df.to_csv(output_dir / "all-benchmarks.csv", index=False)
    zoom_df.to_csv(output_dir / "all-benchmarks-under-1m.csv", index=False)

    md_parts = []
    md_parts.append("# Hashmap benchmark report")
    md_parts.append("")
    md_parts.append(f"Aggregated using **{metric}** as the plotted value.")
    md_parts.append("")
    md_parts.append("This report is generated by `main.py`. The default output directory is `docs/`, so GitHub Pages can serve this file as `index.md` and GitHub will also render `README.md` when browsing the directory.")
    md_parts.append("")
    md_parts.append("## Outputs")
    md_parts.append("")
    md_parts.append("- `all-benchmarks.csv`: full aggregated dataset")
    md_parts.append("- `all-benchmarks-under-1m.csv`: aggregated dataset restricted to `keys <= 1_000_000`")
    md_parts.append("- `insert.csv`, `update.csv`, `retrieve.csv`, `miss.csv`: full per-test CSVs")
    md_parts.append("- `insert-under-1m.csv`, `update-under-1m.csv`, `retrieve-under-1m.csv`, `miss-under-1m.csv`: zoomed per-test CSVs")
    md_parts.append("")
    md_parts.append("## Zoomed report: ≤ 1M keys")
    md_parts.append("")
    md_parts.append("This section focuses on the small/medium map regime, which is often the most relevant range for application code.")
    md_parts.append("")

    for test_name in MODES:
        df_test = zoom_df[zoom_df["test"] == test_name].copy()
        if df_test.empty:
            continue
        chart_path = plot_test_chart(
            df_test,
            test_name,
            output_dir,
            filename=f"{test_name}-under-1m.png",
            zoomed=True,
        )
        df_test.to_csv(output_dir / f"{test_name}-under-1m.csv", index=False)
        _append_test_section(md_parts, f"{test_name.title()} ≤ 1M keys", df_test, chart_path)

    md_parts.append("## Full report")
    md_parts.append("")

    for test_name in MODES:
        df_test = agg_df[agg_df["test"] == test_name].copy()
        if df_test.empty:
            continue
        chart_path = plot_test_chart(df_test, test_name, output_dir)
        df_test.to_csv(output_dir / f"{test_name}.csv", index=False)
        _append_test_section(md_parts, f"{test_name.title()} full range", df_test, chart_path)

    report = "\n".join(md_parts)
    (output_dir / "index.md").write_text(report, encoding="utf-8")
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    print(f"==> wrote report to {output_dir / 'index.md'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and benchmark hashmap implementations, then regenerate the report.",
    )
    parser.add_argument(
        "implementations",
        nargs="*",
        help="implementation directory name(s) under hashmap/ to refresh. If omitted, all implementations are refreshed.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="do not build or run benchmarks; only regenerate docs from existing JSON result files.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list available implementations and exit.",
    )
    parser.add_argument(
        "--metric",
        default="median_ms",
        choices=["mean_ms", "median_ms", "min_ms"],
        help="metric used for charts and report tables.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="report output directory. Defaults to ./docs for GitHub Pages.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not HASHMAP_DIR.is_dir():
        raise SystemExit("missing hashmap/ directory")

    if args.list:
        for impl_dir in discover_implementations(HASHMAP_DIR):
            print(impl_dir.name)
        return

    if not args.report_only:
        impls = select_implementations(HASHMAP_DIR, args.implementations)
        for impl_dir in impls:
            refresh_implementation(impl_dir)
    elif args.implementations:
        print("==> --report-only ignores implementation names; regenerating report from existing results")

    build_benchmark_report(ROOT, args.output_dir, metric=args.metric)


if __name__ == "__main__":
    main()
