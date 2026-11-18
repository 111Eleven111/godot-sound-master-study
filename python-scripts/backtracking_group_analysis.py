"""Test platform revisitation by experience and audio condition.

Backtracking is defined as landing on a platform whose ID appeared earlier in
the same session. All inferential summaries resample participants, preserving
the repeated sessions within each participant.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).parent
DEFAULT_RESULTS = SCRIPT_DIR / "backtracking-results.csv"
DEFAULT_QUESTIONNAIRE = SCRIPT_DIR / "study-data" / "data-with-order.txt"
METRICS = (
    "return_rate",
    "revisited_rate",
    "return_episode_rate",
)


def load_data(results_path: Path, questionnaire_path: Path) -> pd.DataFrame:
    """Load platform-revisit records and attach experience/audio groups."""
    data = pd.read_csv(results_path)
    with questionnaire_path.open(newline="", encoding="utf-8-sig") as file:
        rows = [row for row in csv.reader(file, delimiter=";") if any(row)]

    experience_groups: dict[str, str] = {}
    for index, row in enumerate(rows[1:], start=1):
        experience = float(row[14])
        if experience in (1, 2):
            experience_groups[f"study-p{index}"] = "experience_1_2"
        elif experience in (3, 4):
            experience_groups[f"study-p{index}"] = "experience_3_4"

    data["group"] = data["participant"].map(experience_groups)
    data["return_rate"] = data["return_landings"] / data["platform_landings"]
    data["revisited_rate"] = (
        data["revisited_platforms"] / data["unique_platforms"]
    )
    data["return_episode_rate"] = (
        data["return_episodes"] / data["platform_landings"]
    )
    data["audio_condition"] = data["scenario"].map(
        {"A": "low", "B": "low", "C": "high", "D": "high"}
    )
    if data["group"].isna().any():
        raise ValueError("Some telemetry participants have no experience group")
    return data


def _holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (len(p_values) - rank) * p_values[index])
        adjusted[index] = max(previous, value)
        previous = adjusted[index]
    return adjusted


def bootstrap_group_difference(
    data: pd.DataFrame,
    metric: str,
    iterations: int,
    seed: int,
) -> dict[str, object]:
    participant_values = (
        data.groupby(["participant", "group"], as_index=False)[metric]
        .mean()
    )
    grouped = {
        group: values[metric].to_numpy()
        for group, values in participant_values.groupby("group")
    }
    first, second = sorted(grouped)
    first_values, second_values = grouped[first], grouped[second]
    rng = np.random.default_rng(seed)
    samples = np.asarray(
        [
            rng.choice(first_values, len(first_values), replace=True).mean()
            - rng.choice(second_values, len(second_values), replace=True).mean()
            for _ in range(iterations)
        ]
    )
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "group_a": first,
        "group_b": second,
        "estimate_a_minus_b": float(first_values.mean() - second_values.mean()),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "participant_counts": {
            first: int(len(first_values)),
            second: int(len(second_values)),
        },
    }


def fit_models(data: pd.DataFrame) -> dict[str, object]:
    """Fit LMM and GEE models for revisit rates."""
    import statsmodels.api as sm
    from statsmodels.formula.api import gee, mixedlm

    results: dict[str, object] = {}
    for metric in METRICS:
        formula = (
            f"{metric} ~ C(scenario) + C(play_position) + C(group) "
            "+ C(scenario):C(group)"
        )
        metric_results: dict[str, object] = {"formula": formula}
        for name, fit in (
            (
                "LMM",
                lambda: mixedlm(
                    formula, data, groups=data["participant"]
                ).fit(reml=False, method="lbfgs"),
            ),
            (
                "GEE",
                lambda: gee(
                    formula,
                    "participant",
                    data,
                    cov_struct=sm.cov_struct.Exchangeable(),
                    family=sm.families.Gaussian(),
                ).fit(),
            ),
        ):
            model = fit()
            terms = {
                "experience": "C(group)[T.experience_3_4]",
                "scenario_B_x_experience": (
                    "C(scenario)[T.B]:C(group)[T.experience_3_4]"
                ),
                "scenario_C_x_experience": (
                    "C(scenario)[T.C]:C(group)[T.experience_3_4]"
                ),
                "scenario_D_x_experience": (
                    "C(scenario)[T.D]:C(group)[T.experience_3_4]"
                ),
            }
            metric_results[name] = {
                label: {
                    "coefficient": float(model.params[term]),
                    "p_value": float(model.pvalues[term]),
                }
                for label, term in terms.items()
            }
        results[metric] = metric_results
    return results


def fit_audio_condition_models(data: pd.DataFrame) -> dict[str, object]:
    """Test high- versus low-musicking condition and its interaction."""
    import statsmodels.api as sm
    from statsmodels.formula.api import gee, mixedlm

    results: dict[str, object] = {}
    for metric in METRICS:
        formula = (
            f"{metric} ~ C(audio_condition) + C(play_position) + C(group) "
            "+ C(audio_condition):C(group)"
        )
        term = "C(audio_condition)[T.low]:C(group)[T.experience_3_4]"
        metric_results: dict[str, object] = {"formula": formula}
        for name, fit in (
            (
                "LMM",
                lambda: mixedlm(
                    formula, data, groups=data["participant"]
                ).fit(reml=False, method="lbfgs"),
            ),
            (
                "GEE",
                lambda: gee(
                    formula,
                    "participant",
                    data,
                    cov_struct=sm.cov_struct.Exchangeable(),
                    family=sm.families.Gaussian(),
                ).fit(),
            ),
        ):
            model = fit()
            metric_results[name] = {
                "coefficient": float(model.params[term]),
                "p_value": float(model.pvalues[term]),
            }
        results[metric] = metric_results
    return results


def analyze(
    results_path: Path = DEFAULT_RESULTS,
    questionnaire_path: Path = DEFAULT_QUESTIONNAIRE,
    iterations: int = 5000,
    seed: int = 2026,
) -> dict[str, object]:
    if iterations < 100:
        raise ValueError("iterations must be at least 100")
    data = load_data(results_path, questionnaire_path)
    scenario_tests = fit_models(data)
    audio_tests = fit_audio_condition_models(data)
    scenario_p_values = {
        metric: {
            model: _holm_adjust([
                scenario_tests[metric][model][f"scenario_{scenario}_x_experience"]["p_value"]
                for scenario in ("B", "C", "D")
            ])
            for model in ("LMM", "GEE")
        }
        for metric in METRICS
    }
    for metric in METRICS:
        for model in ("LMM", "GEE"):
            for scenario, adjusted in zip(("B", "C", "D"), scenario_p_values[metric][model]):
                scenario_tests[metric][model][f"scenario_{scenario}_x_experience"]["holm_p_value"] = adjusted

    return {
        "definition": (
            "A return is a platform_landed event whose platform ID was "
            "previously observed in the same session."
        ),
        "participants": int(data["participant"].nunique()),
        "sessions": int(len(data)),
        "group_counts": {
            group: int(data.loc[data["group"] == group, "participant"].nunique())
            for group in sorted(data["group"].unique())
        },
        "descriptive_means": {
            metric: {
                group: float(data.loc[data["group"] == group, metric].mean())
                for group in sorted(data["group"].unique())
            }
            for metric in METRICS
        },
        "audio_condition_means": {
            metric: {
                condition: float(
                    data.loc[data["audio_condition"] == condition, metric].mean()
                )
                for condition in ("low", "high")
            }
            for metric in METRICS
        },
        "bootstrap": {
            metric: bootstrap_group_difference(data, metric, iterations, seed + index)
            for index, metric in enumerate(METRICS)
        },
        "scenario_x_experience": scenario_tests,
        "audio_condition_x_experience": audio_tests,
    }


def write_markdown(result: dict[str, object], path: Path) -> None:
    lines = [
        "# Platform revisitation analysis",
        "",
        "A return means landing on a platform whose ID was previously observed in the same session.",
        "",
        "## Experience-group bootstrap",
        "",
        "| Metric | Estimate (1–2 minus 3–4) | 95% interval |",
        "|---|---:|---:|",
    ]
    labels = {
        "return_rate": "Return landings / platform landings",
        "revisited_rate": "Revisited platforms / unique platforms",
        "return_episode_rate": "Return episodes / platform landings",
    }
    for metric, value in result["bootstrap"].items():
        lines.append(
            f"| {labels[metric]} | {value['estimate_a_minus_b']:.3f} | "
            f"[{value['lower_95']:.3f}, {value['upper_95']:.3f}] |"
        )
    lines.extend([
        "",
        "## Scenario × experience interactions",
        "",
        "P-values are exploratory Wald tests; Holm correction is within the B/C/D family for each metric and model.",
        "",
        "| Metric | Model | B p | B Holm p | C p | C Holm p | D p | D Holm p |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for metric, tests in result["scenario_x_experience"].items():
        for model in ("LMM", "GEE"):
            row = tests[model]
            lines.append(
                f"| {labels[metric]} | {model} | "
                f"{row['scenario_B_x_experience']['p_value']:.4g} | {row['scenario_B_x_experience']['holm_p_value']:.4g} | "
                f"{row['scenario_C_x_experience']['p_value']:.4g} | {row['scenario_C_x_experience']['holm_p_value']:.4g} | "
                f"{row['scenario_D_x_experience']['p_value']:.4g} | {row['scenario_D_x_experience']['holm_p_value']:.4g} |"
            )
    lines.extend([
        "",
        "## High/low audio condition × experience",
        "",
        "| Metric | Model | Coefficient | p-value |",
        "|---|---|---:|---:|",
    ])
    for metric, tests in result["audio_condition_x_experience"].items():
        for model in ("LMM", "GEE"):
            row = tests[model]
            lines.append(
                f"| {labels[metric]} | {model} | {row['coefficient']:.3f} | {row['p_value']:.4g} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--questionnaire", type=Path, default=DEFAULT_QUESTIONNAIRE)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=Path("backtracking-group-results.json"))
    parser.add_argument("--markdown", type=Path, default=Path("backtracking-group-results.md"))
    args = parser.parse_args(argv)
    result = analyze(
        args.results, args.questionnaire, args.iterations, args.seed
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_markdown(result, args.markdown)
    print(f"Wrote {args.output} and {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
