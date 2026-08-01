"""Generate benchmark reports and console dashboards."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from evals.paths import AUTOCLAW_ROOT

BENCHMARK_RESULTS = AUTOCLAW_ROOT / "evals" / "benchmark" / "results.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class BenchmarkDashboard:
    """Generate benchmark reports and visualizations."""

    def __init__(self, results_path: Optional[str] = None):
        self.results_path = Path(results_path or BENCHMARK_RESULTS)
        self.results = self._load_results()

    def _load_results(self) -> List[Dict]:
        if not self.results_path.exists():
            return []
        with open(self.results_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("results", [])
        return data

    def generate_report(self) -> Dict:
        if not self.results:
            return {"error": "No results", "generated_at": _utc_now()}

        by_category: Dict[str, List[Dict]] = defaultdict(list)
        by_variant: Dict[str, List[Dict]] = defaultdict(list)
        by_domain: Dict[str, List[Dict]] = defaultdict(list)
        for r in self.results:
            by_category[r.get("category", "unknown")].append(r)
            combo = f"{r.get('variant_hermes', '?')}+{r.get('variant_laguna', '?')}"
            by_variant[combo].append(r)
            by_domain[r.get("domain") or "general"].append(r)

        report = {
            "generated_at": _utc_now(),
            "total_runs": len(self.results),
            "by_category": {},
            "by_variant": {},
            "by_domain": {},
            "overall": self._calculate_overall_metrics(),
        }
        for category, results in by_category.items():
            report["by_category"][category] = {
                "count": len(results),
                "success_rate": self._calc_success_rate(results),
                "avg_cost": self._calc_avg(results, "cost"),
                "avg_time": self._calc_avg(results, "time_seconds"),
                "avg_quality": self._calc_avg(results, "quality_score"),
                "avg_iterations": self._calc_avg(results, "iterations"),
            }
        for combo, results in by_variant.items():
            report["by_variant"][combo] = {
                "count": len(results),
                "success_rate": self._calc_success_rate(results),
                "avg_cost": self._calc_avg(results, "cost"),
                "avg_time": self._calc_avg(results, "time_seconds"),
                "avg_quality": self._calc_avg(results, "quality_score"),
            }
        for domain, results in by_domain.items():
            report["by_domain"][domain] = {
                "count": len(results),
                "success_rate": self._calc_success_rate(results),
                "avg_cost": self._calc_avg(results, "cost"),
                "avg_quality": self._calc_avg(results, "quality_score"),
            }
        return report

    def _calculate_overall_metrics(self) -> Dict:
        if not self.results:
            return {}
        total_time = sum(r.get("time_seconds", 0) or 0 for r in self.results)
        expected_costs = [
            float(r.get("expected_cost") or 0)
            for r in self.results
            if (r.get("expected_cost") or 0) > 0
        ]
        actual_costs = [
            float(r.get("cost") or 0)
            for r in self.results
            if (r.get("expected_cost") or 0) > 0
        ]
        cost_efficiency = 0.0
        if expected_costs and sum(actual_costs) > 0:
            # Lower is better: actual / expected (<1 means under budget).
            cost_efficiency = round(sum(actual_costs) / sum(expected_costs), 4)
        planning_failed = sum(1 for r in self.results if r.get("planning_failed"))
        handoff_failed = sum(1 for r in self.results if r.get("handoff_failed"))
        n = len(self.results)
        return {
            "success_rate": self._calc_success_rate(self.results),
            "avg_cost": self._calc_avg(self.results, "cost"),
            "avg_time_seconds": self._calc_avg(self.results, "time_seconds"),
            "avg_quality": self._calc_avg(self.results, "quality_score"),
            "avg_iterations": self._calc_avg(self.results, "iterations"),
            "total_cost": sum(r.get("cost", 0) or 0 for r in self.results),
            "total_time_seconds": total_time,
            "cost_efficiency": cost_efficiency,
            "spec_rejection_rate": round(planning_failed / n, 4) if n else 0.0,
            "handoff_failure_rate": round(handoff_failed / n, 4) if n else 0.0,
            "spec_acceptance_rate": round(1 - (planning_failed / n), 4) if n else 0.0,
            "throughput_tasks_per_hour": round(n / (total_time / 3600), 4)
            if total_time > 0
            else 0.0,
        }

    def _calc_success_rate(self, results: List[Dict]) -> float:
        successful = sum(1 for r in results if r.get("status") == "success")
        return round(successful / len(results), 4) if results else 0.0

    def _calc_avg(self, results: List[Dict], field: str) -> float:
        values = [float(r.get(field) or 0) for r in results if r.get(field) is not None]
        return round(sum(values) / len(values), 4) if values else 0.0

    def print_report(self) -> None:
        report = self.generate_report()
        print("\n" + "=" * 70)
        print("BENCHMARK DASHBOARD")
        print("=" * 70)
        if report.get("error"):
            print(f"\n{report['error']}")
            print("=" * 70)
            return

        print(f"\nGenerated: {report.get('generated_at', 'N/A')}")
        print(f"Total Runs: {report.get('total_runs', 0)}")

        print("\nOVERALL METRICS:")
        for metric, value in report.get("overall", {}).items():
            if isinstance(value, float):
                print(f"  {metric:20s}: {value:.4f}")
            else:
                print(f"  {metric:20s}: {value}")

        print("\nBY CATEGORY:")
        for category, metrics in report.get("by_category", {}).items():
            print(f"\n  {category.upper()}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"    {metric:20s}: {value:.4f}")
                else:
                    print(f"    {metric:20s}: {value}")

        print("\nBY VARIANT COMBO:")
        for combo, metrics in report.get("by_variant", {}).items():
            print(f"\n  {combo}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"    {metric:20s}: {value:.4f}")
                else:
                    print(f"    {metric:20s}: {value}")

        print("\nBY DOMAIN:")
        for domain, metrics in report.get("by_domain", {}).items():
            print(f"\n  {domain}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"    {metric:20s}: {value:.4f}")
                else:
                    print(f"    {metric:20s}: {value}")
        print("\n" + "=" * 70)

    def generate_comparison_report(self, results_path_1: str, results_path_2: str) -> Dict:
        dashboard_1 = BenchmarkDashboard(results_path_1)
        dashboard_2 = BenchmarkDashboard(results_path_2)
        report_1 = dashboard_1.generate_report()
        report_2 = dashboard_2.generate_report()

        comparison = {}
        for metric in ("success_rate", "avg_cost", "avg_time_seconds", "avg_quality"):
            if metric in report_1.get("overall", {}) and metric in report_2.get("overall", {}):
                val_1 = report_1["overall"][metric]
                val_2 = report_2["overall"][metric]
                if metric in ("avg_cost", "avg_time_seconds"):
                    improvement = ((val_1 - val_2) / val_1 * 100) if val_1 else 0
                else:
                    improvement = ((val_2 - val_1) / val_1 * 100) if val_1 else 0
                comparison[metric] = {
                    "before": val_1,
                    "after": val_2,
                    "improvement": round(improvement, 2),
                    "direction": "improved" if improvement > 0 else "degraded",
                }
        return comparison

    def save_report(self, path: Optional[Path] = None) -> Path:
        out = Path(path or self.results_path.parent / "report.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        report = self.generate_report()
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        return out

    def write_github_summary(self, path: Optional[Path] = None) -> str:
        """Render a compact Markdown summary for GitHub Actions step summaries."""
        report = self.generate_report()
        if report.get("error"):
            md = f"### Benchmark dashboard\n\n_{report['error']}_\n"
        else:
            overall = report.get("overall") or {}
            lines = [
                "### Benchmark summary",
                "",
                f"- Generated: `{report.get('generated_at', 'n/a')}`",
                f"- Total runs: **{report.get('total_runs', 0)}**",
                f"- Success rate: **{float(overall.get('success_rate', 0)):.4f}**",
                f"- Avg quality: **{float(overall.get('avg_quality', 0)):.4f}**",
                f"- Avg cost: **{float(overall.get('avg_cost', 0)):.4f}**",
                f"- Spec rejection: **{float(overall.get('spec_rejection_rate', 0)):.4f}**",
                f"- Handoff failure: **{float(overall.get('handoff_failure_rate', 0)):.4f}**",
                "",
                "| Category | Count | Success | Quality |",
                "| --- | ---: | ---: | ---: |",
            ]
            for category, metrics in sorted((report.get("by_category") or {}).items()):
                lines.append(
                    f"| {category} | {metrics.get('count', 0)} | "
                    f"{float(metrics.get('success_rate', 0)):.4f} | "
                    f"{float(metrics.get('avg_quality', 0)):.4f} |"
                )
            lines.append("")
            md = "\n".join(lines)
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(md, encoding="utf-8")
        return md
