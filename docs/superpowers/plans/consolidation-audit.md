## csv/scripts (CSV reads, figure writes, sibling imports)
csv/scripts/01_overview.py:2:from __future__ import annotations
csv/scripts/01_overview.py:4:from _loader import load, save_table
csv/scripts/10_haiku_collapse.py:7:from __future__ import annotations
csv/scripts/10_haiku_collapse.py:10:from _loader import load, fig_path, save_table, FRAME_ORDER, INCENTIVE_ORDER, DIFFICULTY_ORDER
csv/scripts/10_haiku_collapse.py:60:    fig.savefig(fig_path("10_haiku_collapse_grid"), dpi=150)
csv/scripts/10_haiku_collapse.py:78:    fig.savefig(fig_path("10_haiku_collapse_by_frame"), dpi=150)
csv/scripts/06_cluster_bootstrap_ci.py:14:from __future__ import annotations
csv/scripts/06_cluster_bootstrap_ci.py:17:from _loader import load, save_table
csv/scripts/06_cluster_bootstrap_ci.py:21:_spec = importlib.util.spec_from_file_location("vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py"))
csv/scripts/08_paired_head_to_head.py:25:from __future__ import annotations
csv/scripts/08_paired_head_to_head.py:32:from _loader import load, save_table, fig_path
csv/scripts/08_paired_head_to_head.py:35:    "vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py")
csv/scripts/08_paired_head_to_head.py:140:    fig.savefig(fig_path(out), dpi=150)
csv/scripts/03_axis_effects.py:2:from __future__ import annotations
csv/scripts/03_axis_effects.py:6:from _loader import load, save_table, fig_path, FRAME_ORDER, INCENTIVE_ORDER, DIFFICULTY_ORDER
csv/scripts/03_axis_effects.py:33:    fig.savefig(fig_path(out), dpi=150)
csv/scripts/03_axis_effects.py:56:    fig.savefig(fig_path(f"03_frame_incentive_{task}"), dpi=150)
csv/scripts/09_capability_analysis.py:23:from __future__ import annotations
csv/scripts/09_capability_analysis.py:29:from _loader import load, save_table, fig_path
csv/scripts/09_capability_analysis.py:32:    "vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py")
csv/scripts/09_capability_analysis.py:217:    fig.savefig(fig_path("09_tier_buckets"), dpi=150)
csv/scripts/09_capability_analysis.py:239:    fig.savefig(fig_path("09_recency_deltas"), dpi=150)
csv/scripts/07_within_task_correlations.py:14:from __future__ import annotations
csv/scripts/07_within_task_correlations.py:18:from _loader import load, save_table, fig_path
csv/scripts/07_within_task_correlations.py:68:    fig.savefig(fig_path(out), dpi=150)
csv/scripts/05_variance_decomposition.py:19:from __future__ import annotations
csv/scripts/05_variance_decomposition.py:23:from _loader import load, save_table, fig_path
csv/scripts/05_variance_decomposition.py:144:    fig.savefig(fig_path("05_variance_stacked"), dpi=150)
csv/scripts/04_interactions.py:8:from __future__ import annotations
csv/scripts/04_interactions.py:12:from _loader import load, save_table, fig_path, FRAME_ORDER
csv/scripts/04_interactions.py:55:    fig.savefig(fig_path(out), dpi=150)
csv/scripts/02_model_ranking.py:12:from __future__ import annotations
csv/scripts/02_model_ranking.py:18:from _loader import load, save_table, fig_path
csv/scripts/02_model_ranking.py:21:    "vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py")
csv/scripts/02_model_ranking.py:86:    fig.savefig(fig_path(out), dpi=150)
csv/scripts/_loader.py:2:from __future__ import annotations
csv/scripts/_loader.py:6:CSV_PATH = Path(__file__).resolve().parent.parent / "results.csv"
csv/scripts/_loader.py:7:OUT_DIR = Path(__file__).resolve().parent.parent / "out"
csv/scripts/_loader.py:19:    df = pd.read_csv(CSV_PATH, dtype=DTYPES, low_memory=False)
csv/scripts/_loader.py:33:    df.to_csv(path, index=True)

## paper/newer_analysis/scripts
paper/newer_analysis/scripts/02_task_model_interaction.py:14:from __future__ import annotations
paper/newer_analysis/scripts/02_task_model_interaction.py:23:ROOT = Path(__file__).resolve().parents[2]
paper/newer_analysis/scripts/02_task_model_interaction.py:25:OUT = Path(__file__).resolve().parents[1] / "out"
paper/newer_analysis/scripts/02_task_model_interaction.py:28:df = pd.read_csv(CSV, low_memory=False)
paper/newer_analysis/scripts/02_task_model_interaction.py:59:with open(OUT / "02_interaction_test.txt", "w") as f:
paper/newer_analysis/scripts/02_task_model_interaction.py:75:cell.to_csv(OUT / "02_cell_residuals.csv", index=False)
paper/newer_analysis/scripts/01_mixed_effects.py:18:from __future__ import annotations
paper/newer_analysis/scripts/01_mixed_effects.py:27:ROOT = Path(__file__).resolve().parents[2]
paper/newer_analysis/scripts/01_mixed_effects.py:29:OUT = Path(__file__).resolve().parents[1] / "out"
paper/newer_analysis/scripts/01_mixed_effects.py:33:df = pd.read_csv(CSV, low_memory=False)
paper/newer_analysis/scripts/01_mixed_effects.py:112:coef_df.to_csv(OUT / "01_mixed_effects_coefs.csv", index=False)
paper/newer_analysis/scripts/03_multiple_testing.py:10:from __future__ import annotations
paper/newer_analysis/scripts/03_multiple_testing.py:17:OUT = Path(__file__).resolve().parents[1] / "out"
paper/newer_analysis/scripts/03_multiple_testing.py:84:df.to_csv(OUT / "03_multiple_testing.csv", index=False)
paper/newer_analysis/scripts/05_refusal_scan.py:16:from __future__ import annotations
paper/newer_analysis/scripts/05_refusal_scan.py:25:ROOT = Path("/home/borneans/Documents/TAICI/manipulation-bench/paper")
paper/newer_analysis/scripts/05_refusal_scan.py:26:OUT = Path(__file__).resolve().parents[1] / "out" / "05_refusals"
paper/newer_analysis/scripts/05_refusal_scan.py:153:df.to_csv(OUT / "per_sample.csv", index=False)
paper/newer_analysis/scripts/05_refusal_scan.py:164:summary.to_csv(OUT / "task_model_summary.csv", index=False)
paper/newer_analysis/scripts/05_refusal_scan.py:174:fsummary.to_csv(OUT / "task_frame_summary.csv", index=False)
paper/newer_analysis/scripts/incentive_forest.py:15:from __future__ import annotations
paper/newer_analysis/scripts/incentive_forest.py:23:REPO = Path(__file__).resolve().parents[3]
paper/newer_analysis/scripts/incentive_forest.py:53:    df = pd.read_csv(CSV, low_memory=False)
paper/newer_analysis/scripts/incentive_forest.py:83:    out.to_csv(OUT_CSV, index=False)
paper/newer_analysis/scripts/incentive_forest.py:130:        fig.savefig(path, dpi=200, bbox_inches="tight")
paper/newer_analysis/scripts/05_spearman_bootstrap.py:31:from __future__ import annotations
paper/newer_analysis/scripts/05_spearman_bootstrap.py:38:ROOT = Path(__file__).resolve().parents[2]
paper/newer_analysis/scripts/05_spearman_bootstrap.py:40:OUT = Path(__file__).resolve().parents[1] / "out"
paper/newer_analysis/scripts/05_spearman_bootstrap.py:52:df = pd.read_csv(CSV, low_memory=False)
paper/newer_analysis/scripts/05_spearman_bootstrap.py:221:pd.DataFrame(per_pair, columns=["pair", "rho_point", "rho_ci_low", "rho_ci_high"]).to_csv(
paper/newer_analysis/scripts/05_spearman_bootstrap.py:225:with open(OUT / "05_spearman_bootstrap_summary.txt", "w") as f:
paper/newer_analysis/scripts/04_incentive_traces.py:17:from __future__ import annotations
paper/newer_analysis/scripts/04_incentive_traces.py:26:LOG = Path("/home/borneans/Documents/TAICI/manipulation-bench/paper/task1_bargaining/eval_log.eval")
paper/newer_analysis/scripts/04_incentive_traces.py:27:OUT = Path(__file__).resolve().parents[1] / "out" / "04_traces"
paper/newer_analysis/scripts/04_incentive_traces.py:111:with open(OUT / "matched_pairs.json", "w") as f:

## paper/capability_eval/scripts
paper/capability_eval/scripts/capability_clustering.py:13:from __future__ import annotations
paper/capability_eval/scripts/capability_clustering.py:24:from _capability_io import ANALYSIS_DIR, FIG_DIR, FRAMES, TASKS, ensure_dirs, load_joined
paper/capability_eval/scripts/capability_clustering.py:85:    fig.savefig(FIG_DIR / "capability_clustering_pca.png", dpi=150)
paper/capability_eval/scripts/capability_clustering.py:100:    with open(ANALYSIS_DIR / "capability_clustering.json", "w", encoding="utf-8") as f:
paper/capability_eval/scripts/capability_frontier_lift.py:12:from __future__ import annotations
paper/capability_eval/scripts/capability_frontier_lift.py:20:from _capability_io import ANALYSIS_DIR, FIG_DIR, TASKS, ensure_dirs, load_joined
paper/capability_eval/scripts/capability_frontier_lift.py:90:    with open(ANALYSIS_DIR / "capability_frontier_lift.json", "w", encoding="utf-8") as f:
paper/capability_eval/scripts/capability_frontier_lift.py:121:        fig.savefig(FIG_DIR / "capability_frontier_lift.png", dpi=150)
paper/capability_eval/scripts/capability_response_surface.py:14:from __future__ import annotations
paper/capability_eval/scripts/capability_response_surface.py:21:from _capability_io import (
paper/capability_eval/scripts/capability_response_surface.py:82:    fig.savefig(out_path, dpi=150)
paper/capability_eval/scripts/capability_response_surface.py:102:    with open(ANALYSIS_DIR / "response_surface_by_tier.json", "w", encoding="utf-8") as f:
paper/capability_eval/scripts/capability_anova.py:12:from __future__ import annotations
paper/capability_eval/scripts/capability_anova.py:20:from _capability_io import ANALYSIS_DIR, ensure_dirs, load_joined, TASKS
paper/capability_eval/scripts/capability_anova.py:63:    with open(ANALYSIS_DIR / "capability_anova.json", "w", encoding="utf-8") as f:
paper/capability_eval/scripts/_capability_io.py:12:from __future__ import annotations
paper/capability_eval/scripts/_capability_io.py:18:ROOT = Path(__file__).resolve().parents[2]
paper/capability_eval/scripts/_capability_io.py:33:    df = pd.read_csv(CAPABILITY_CSV)
paper/capability_eval/scripts/_capability_io.py:40:    res = pd.read_csv(RESULTS_CSV, low_memory=False)
paper/capability_eval/scripts/capability_regression.py:15:from __future__ import annotations
paper/capability_eval/scripts/capability_regression.py:24:from _capability_io import ANALYSIS_DIR, FIG_DIR, FRAMES, INCENTIVES, DIFFICULTIES, TASKS, ensure_dirs, load_joined
paper/capability_eval/scripts/capability_regression.py:119:    fig.savefig(out_path, dpi=150)
paper/capability_eval/scripts/capability_regression.py:137:    with open(ANALYSIS_DIR / "capability_regression.json", "w", encoding="utf-8") as f:
paper/capability_eval/scripts/capability_analysis.py:12:from __future__ import annotations
paper/capability_eval/scripts/capability_analysis.py:24:ROOT = Path(__file__).resolve().parents[2]
paper/capability_eval/scripts/capability_analysis.py:46:    with open(CAPABILITY, encoding="utf-8") as f:
paper/capability_eval/scripts/capability_analysis.py:55:    with open(RESULTS, encoding="utf-8") as f:
paper/capability_eval/scripts/capability_analysis.py:178:    fig.savefig(out_path, dpi=150)
paper/capability_eval/scripts/capability_analysis.py:204:    fig.savefig(out_path, dpi=150)
paper/capability_eval/scripts/capability_analysis.py:225:    fig.savefig(out_path, dpi=150)
paper/capability_eval/scripts/capability_analysis.py:250:    with open(out_json, "w", encoding="utf-8") as f:

## paper/cross_task/scripts (existing — will be sub-namespaced)
paper/cross_task/scripts/bootstrap_cis.py:19:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/bootstrap_cis.py:137:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/bootstrap_cis.py:166:        out_dir = Path("paper") / task["dir"] / "analysis"
paper/cross_task/scripts/bootstrap_cis.py:180:        with open(out_json, "w", encoding="utf-8") as f:
paper/cross_task/scripts/bootstrap_cis.py:189:        fig_path = Path("paper") / task["dir"] / "figures" / "fig5_slopes_with_ci.pdf"
paper/cross_task/scripts/combine_eval_logs.py:95:    out_path = Path(out_path_str)
paper/cross_task/scripts/aggregate.py:27:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/aggregate.py:30:OUT_DIR = Path("paper/cross_task/analysis")
paper/cross_task/scripts/aggregate.py:31:FIG_DIR = Path("paper/cross_task/figures")
paper/cross_task/scripts/aggregate.py:61:    p = Path("paper") / task_dir / "analysis" / "prereg_results.json"
paper/cross_task/scripts/aggregate.py:67:    with open(p, encoding="utf-8") as f:
paper/cross_task/scripts/aggregate.py:185:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/aggregate.py:220:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/aggregate.py:257:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/aggregate.py:329:    with open(out_json, "w", encoding="utf-8") as f:
paper/cross_task/scripts/cohens_d.py:25:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/cohens_d.py:225:    out = Path("paper") / task["dir"] / "figures" / "fig6_cohens_d_heatmap.pdf"
paper/cross_task/scripts/cohens_d.py:226:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/cohens_d.py:241:        out_dir = Path("paper") / task["dir"] / "analysis"
paper/cross_task/scripts/cohens_d.py:270:        with open(out_json, "w", encoding="utf-8") as f:
paper/cross_task/scripts/append_t6_to_results.py:1:"""Append T6 inbox rows to paper/cross_task/results.csv.
paper/cross_task/scripts/append_t6_to_results.py:3:Memory-light alternative to a full eval_logs_to_csv rerun: reads only the T6
paper/cross_task/scripts/append_t6_to_results.py:5:schema as the existing results.csv, then concatenates.
paper/cross_task/scripts/append_t6_to_results.py:20:REPO_ROOT = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/append_t6_to_results.py:21:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/append_t6_to_results.py:25:EXISTING_CSV = REPO_ROOT / "paper/cross_task/results.csv"
paper/cross_task/scripts/append_t6_to_results.py:26:DEST_CSV = REPO_ROOT / "paper/cross_task/results.csv"
paper/cross_task/scripts/append_t6_to_results.py:27:CSV_MIRROR = REPO_ROOT / "csv/results.csv"
paper/cross_task/scripts/append_t6_to_results.py:114:    with EXISTING_CSV.open("r", encoding="utf-8", newline="") as f:
paper/cross_task/scripts/append_t6_to_results.py:132:    with EXISTING_CSV.open("r", encoding="utf-8", newline="") as src, \
paper/cross_task/scripts/append_t6_to_results.py:133:         tmp_out.open("w", encoding="utf-8", newline="") as dst:
paper/cross_task/scripts/clustering.py:23:OUT_DIR = Path("paper/cross_task/analysis")
paper/cross_task/scripts/clustering.py:24:FIG_DIR = Path("paper/cross_task/figures")
paper/cross_task/scripts/clustering.py:39:    d = json.load(open(PROFILES))
paper/cross_task/scripts/clustering.py:70:    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/clustering.py:85:    with open(out_path, "w", encoding="utf-8") as f:
paper/cross_task/scripts/clustering.py:119:    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/clustering.py:146:    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/append_t6_to_csv.py:1:"""Append T6 (inbox triage) rows to paper/cross_task/results.csv.
paper/cross_task/scripts/append_t6_to_csv.py:8:Picks up the same glob set as eval_logs_to_csv.py's DEFAULT_T6_SWEEP_GLOBS,
paper/cross_task/scripts/append_t6_to_csv.py:10:match eval_logs_to_csv.py exactly.
paper/cross_task/scripts/append_t6_to_csv.py:19:REPO_ROOT = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/append_t6_to_csv.py:20:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/append_t6_to_csv.py:22:from eval_logs_to_csv import (  # noqa: E402
paper/cross_task/scripts/append_t6_to_csv.py:28:DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"
paper/cross_task/scripts/append_t6_to_csv.py:46:        raise SystemExit(f"{out_path} does not exist; run eval_logs_to_csv.py first")
paper/cross_task/scripts/append_t6_to_csv.py:66:    with out_path.open("r", encoding="utf-8") as f:
paper/cross_task/scripts/append_t6_to_csv.py:82:        existing_df = pd.read_csv(out_path, low_memory=False)
paper/cross_task/scripts/append_t6_to_csv.py:90:        merged.to_csv(out_path, index=False)
paper/cross_task/scripts/append_t6_to_csv.py:94:        with out_path.open("a", newline="", encoding="utf-8") as f:
paper/cross_task/scripts/eval_logs_to_csv.py:10:    python paper/cross_task/scripts/eval_logs_to_csv.py
paper/cross_task/scripts/eval_logs_to_csv.py:11:    python paper/cross_task/scripts/eval_logs_to_csv.py -o foo.csv
paper/cross_task/scripts/eval_logs_to_csv.py:12:    python paper/cross_task/scripts/eval_logs_to_csv.py --logs 'logs/*.eval'
paper/cross_task/scripts/eval_logs_to_csv.py:30:REPO_ROOT = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/eval_logs_to_csv.py:31:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/eval_logs_to_csv.py:62:DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"
paper/cross_task/scripts/eval_logs_to_csv.py:77:        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
paper/cross_task/scripts/eval_logs_to_csv.py:81:            Path(p) for p in glob.glob(str(REPO_ROOT / pattern))
paper/cross_task/scripts/eval_logs_to_csv.py:82:            if Path(p).suffix == ".eval"
paper/cross_task/scripts/eval_logs_to_csv.py:182:        print(f"[eval_logs_to_csv] {path}: unknown task, skipping", file=sys.stderr)
paper/cross_task/scripts/eval_logs_to_csv.py:208:    print(f"[eval_logs_to_csv] {path.name}: {len(rows)} rows", file=sys.stderr)
paper/cross_task/scripts/eval_logs_to_csv.py:261:        print("[eval_logs_to_csv] no input logs found", file=sys.stderr)
paper/cross_task/scripts/eval_logs_to_csv.py:265:        tmp_path = Path(tmp_dir)
paper/cross_task/scripts/eval_logs_to_csv.py:279:            with tmp_file.open("w", encoding="utf-8") as f:
paper/cross_task/scripts/eval_logs_to_csv.py:287:            print("[eval_logs_to_csv] no samples extracted", file=sys.stderr)
paper/cross_task/scripts/eval_logs_to_csv.py:295:        with args.output.open("w", newline="", encoding="utf-8") as csv_fh:
paper/cross_task/scripts/eval_logs_to_csv.py:303:                with tmp_file.open("r", encoding="utf-8") as jf:
paper/cross_task/scripts/eval_logs_to_csv.py:308:        f"[eval_logs_to_csv] wrote {total_rows} rows × {len(ordered_cols)} cols"
paper/cross_task/scripts/analyze_response_surface.py:48:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/analyze_response_surface.py:49:sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
paper/cross_task/scripts/analyze_response_surface.py:135:    """Load rows from the canonical results.csv via load_corpus().
paper/cross_task/scripts/analyze_response_surface.py:375:    with open(path, "w", encoding="utf-8", newline="") as f:
paper/cross_task/scripts/analyze_response_surface.py:651:    ap.add_argument("--logs", nargs="*", default=None, help="Ignored (kept for CLI compatibility; data is loaded from results.csv)")
paper/cross_task/scripts/explore.py:25:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/explore.py:31:OUT = Path("paper/cross_task/figures")
paper/cross_task/scripts/explore.py:177:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/explore.py:258:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/explore.py:313:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/explore.py:366:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/explore.py:408:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/explore.py:477:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/explore.py:560:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/regression.py:39:REPO = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/regression.py:40:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/regression.py:331:        with open(out_path, "w", encoding="utf-8") as f:
paper/cross_task/scripts/v2_figures.py:25:REPO = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/v2_figures.py:26:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/v2_figures.py:104:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/v2_figures.py:164:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/v2_figures.py:242:    fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/response_surface.py:24:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/response_surface.py:192:    out = Path("paper") / task["dir"] / "figures" / "fig7_response_surface.pdf"
paper/cross_task/scripts/response_surface.py:193:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/frontier_lift.py:261:    out_dir = Path("paper/cross_task/analysis")
paper/cross_task/scripts/frontier_lift.py:263:    with open(out_dir / "frontier_lift.json", "w", encoding="utf-8") as f:
paper/cross_task/scripts/frontier_lift.py:325:    out = Path("paper/cross_task/figures") / "fig_frontier_lift.pdf"
paper/cross_task/scripts/frontier_lift.py:327:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/variance_decomposition.py:37:REPO = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/variance_decomposition.py:38:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/variance_decomposition.py:189:    with open(out_path, "w", encoding="utf-8") as f:
paper/cross_task/scripts/sample_distributions.py:18:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/sample_distributions.py:148:    out = Path("paper") / task["dir"] / "figures" / "fig10_sample_distributions.pdf"
paper/cross_task/scripts/sample_distributions.py:150:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/ranking_stability_v2.py:38:REPO = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/ranking_stability_v2.py:39:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/ranking_stability_v2.py:250:    with open(out_path, "w", encoding="utf-8") as f:
paper/cross_task/scripts/ranking_stability_v2.py:257:    with open(out_path2, "w", encoding="utf-8") as f:
paper/cross_task/scripts/ranking_stability_v2.py:266:    with open(out_path3, "w", encoding="utf-8") as f:
paper/cross_task/scripts/load.py:28:REPO_ROOT = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/load.py:267:RESULTS_CSV = REPO_ROOT / "paper/cross_task/results.csv"
paper/cross_task/scripts/load.py:273:    """Read paper/cross_task/results.csv and shape it like _row_from_sample output.
paper/cross_task/scripts/load.py:286:    df = pd.read_csv(csv_path, low_memory=False)
paper/cross_task/scripts/load.py:342:        source: "csv" reads paper/cross_task/results.csv (~30s for full corpus).
paper/cross_task/scripts/load.py:359:                "regenerate it with `python paper/cross_task/scripts/eval_logs_to_csv.py`"
paper/cross_task/scripts/ranking_stability_v1.py:23:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/ranking_stability_v1.py:112:    out = Path("paper/cross_task/figures") / "fig_ranking_stability.pdf"
paper/cross_task/scripts/ranking_stability_v1.py:113:    fig.savefig(out, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/ranking_stability_v1.py:141:    json_path = Path("paper/cross_task/analysis/ranking_stability.json")
paper/cross_task/scripts/ranking_stability_v1.py:142:    with open(json_path, "w", encoding="utf-8") as f:
paper/cross_task/scripts/_v2_smoke.py:24:REPO = Path(__file__).resolve().parents[3]
paper/cross_task/scripts/_v2_smoke.py:25:sys.path.insert(0, str(Path(__file__).parent))
paper/cross_task/scripts/surprise_residuals.py:24:sys.path.insert(0, str(Path(__file__).resolve().parent))
paper/cross_task/scripts/surprise_residuals.py:228:            Path("paper/cross_task/figures") / f"fig_residual_{task['name'].split()[0].lower()}.pdf"
paper/cross_task/scripts/surprise_residuals.py:231:        fig.savefig(out_path, dpi=150, bbox_inches="tight")
paper/cross_task/scripts/surprise_residuals.py:237:    out_json = Path("paper/cross_task/analysis/residuals.json")
paper/cross_task/scripts/surprise_residuals.py:238:    with open(out_json, "w", encoding="utf-8") as f:
