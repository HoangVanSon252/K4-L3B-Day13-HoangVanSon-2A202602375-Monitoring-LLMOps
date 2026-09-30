from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from string import Template
from typing import Any

import yaml


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((p / 100) * len(ordered) + 0.5) - 1))
    return ordered[index]


def load_records(path: Path, minutes: int) -> tuple[list[dict[str, Any]], datetime, datetime]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            item["_time"] = parse_ts(item["ts"])
            records.append(item)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    if not records:
        now = datetime.now(timezone.utc)
        return [], now - timedelta(minutes=minutes), now
    end = max(item["_time"] for item in records)
    start = end - timedelta(minutes=minutes)
    return [item for item in records if item["_time"] >= start], start, end


def status(value: float, op: str, threshold: float) -> str:
    passed = value <= threshold if op == "lte" else value >= threshold
    return "healthy" if passed else "alert"


def spark(values: list[float], color: str) -> str:
    values = values[-24:] or [0]
    ceiling = max(values) or 1
    bars = "".join(
        f'<i style="height:{max(5, round(value / ceiling * 100))}%;background:{color}" title="{value:.4f}"></i>'
        for value in values
    )
    return f'<div class="spark">{bars}</div>'


def render(log_path: Path, config_path: Path, output_path: Path) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))["dashboard"]
    records, start, end = load_records(log_path, int(config["time_range_minutes"]))
    requests = [item for item in records if item.get("event") == "request_received"]
    responses = [item for item in records if item.get("event") == "response_sent"]
    failures = [item for item in records if item.get("event") == "request_failed"]
    latencies = [float(item.get("latency_ms", 0)) for item in responses]
    ttfts = [float(item.get("ttft_ms", 0)) for item in responses]
    costs = [float(item.get("cost_usd", 0)) for item in responses]
    quality = [float(item["quality_score"]) for item in responses if item.get("quality_score") is not None]
    retrievals = [item for item in responses if item.get("tool_success") is not None]
    error_rate = len(failures) / len(requests) * 100 if requests else 0.0
    retrieval_rate = sum(item.get("tool_success") is True for item in retrievals) / len(retrievals) * 100 if retrievals else 0.0
    duration = max((end - start).total_seconds() / 60, 1)

    values = {
        "latency": percentile(latencies, 95),
        "traffic": len(requests) / duration,
        "errors": error_rate,
        "cost": sum(costs),
        "tokens": sum(int(item.get("tokens_in", 0)) + int(item.get("tokens_out", 0)) for item in responses),
        "quality": mean(quality) if quality else 0.0,
    }
    panels = {panel["id"]: panel for panel in config["panels"]}

    cards = [
        ("Latency & TTFT", f'{values["latency"]:.0f} ms', f'P50 {percentile(latencies, 50):.0f} · P95 {values["latency"]:.0f} · P99 {percentile(latencies, 99):.0f} · TTFT P95 {percentile(ttfts, 95):.0f} ms', spark(latencies, "#7c3aed"), "latency"),
        ("Request traffic", f'{len(requests)} requests', f'{values["traffic"]:.2f} requests/min · {len(responses)} completed', spark([1.0 for _ in requests], "#0284c7"), "traffic"),
        ("Errors & retrieval", f'{error_rate:.2f}% errors', f'{len(failures)} failed · retrieval success {retrieval_rate:.1f}%', spark([0 if item.get("tool_success") else 1 for item in retrievals], "#dc2626"), "errors"),
        ("Cost over time", f'${sum(costs):.4f}', f'Average ${mean(costs):.6f}/response', spark(costs, "#059669"), "cost"),
        ("Token usage", f'{values["tokens"]:,.0f}', f'Input {sum(int(x.get("tokens_in", 0)) for x in responses):,} · Output {sum(int(x.get("tokens_out", 0)) for x in responses):,}', spark([float(x.get("tokens_in", 0)) + float(x.get("tokens_out", 0)) for x in responses], "#d97706"), "tokens"),
        ("Quality proxy", f'{values["quality"]:.2f}', f'Average score · target ≥ {panels["quality"]["threshold"]["value"]}', spark(quality, "#db2777"), "quality"),
    ]

    card_html = []
    for title, metric, detail, chart, panel_id in cards:
        threshold = panels[panel_id]["threshold"]
        state = status(values[panel_id], threshold["operator"], float(threshold["value"]))
        card_html.append(f'''<section class="panel {state}">
          <header><h2>{html.escape(title)}</h2><span>{state.upper()}</span></header>
          <strong>{html.escape(metric)}</strong><p>{html.escape(detail)}</p>{chart}
          <footer>{html.escape(panels[panel_id]["query"])}</footer>
        </section>''')

    template = Template('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>$title</title>
<style>
:root{font-family:Inter,Segoe UI,sans-serif;color:#172033;background:#f5f7fb}*{box-sizing:border-box}body{margin:0}main{max-width:1440px;margin:auto;padding:28px}nav{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #dce2eb;padding-bottom:18px}h1{font-size:22px;margin:0;letter-spacing:0}.sub{color:#64748b;font-size:13px;margin-top:6px}.range{background:#fff;border:1px solid #dce2eb;padding:10px 12px;border-radius:6px;font-size:13px}.summary{display:flex;gap:22px;margin:22px 0;color:#475569;font-size:13px}.summary b{color:#172033}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.panel{background:#fff;border:1px solid #dce2eb;border-top:3px solid #16a34a;border-radius:7px;padding:18px;min-height:248px;box-shadow:0 2px 8px #1720330b}.panel.alert{border-top-color:#dc2626}.panel header{display:flex;align-items:center;justify-content:space-between}.panel h2{font-size:15px;margin:0}.panel header span{font-size:10px;font-weight:700;color:#15803d;background:#dcfce7;padding:5px 7px;border-radius:4px}.panel.alert header span{color:#b91c1c;background:#fee2e2}.panel strong{display:block;font-size:30px;margin-top:20px}.panel p{color:#64748b;font-size:13px;min-height:34px}.spark{height:72px;display:flex;align-items:flex-end;gap:4px;border-bottom:1px solid #cbd5e1;padding-top:8px}.spark i{display:block;flex:1;min-width:3px;opacity:.85;border-radius:2px 2px 0 0}.panel footer{margin-top:14px;color:#94a3b8;font:10px Consolas,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.note{margin-top:18px;padding:12px 14px;background:#eef2ff;border-left:3px solid #4f46e5;font-size:12px;color:#475569}@media(max-width:900px){.grid{grid-template-columns:1fr}.summary{flex-wrap:wrap}main{padding:18px}}
</style></head><body><main><nav><div><h1>$title</h1><div class="sub">Operational dashboard · source: $source</div></div><div class="range">Last $minutes min · refresh $refresh s</div></nav><div class="summary"><span>Window <b>$start – $end UTC</b></span><span>Records <b>$records</b></span><span>Completed <b>$responses</b></span></div><div class="grid">$cards</div><div class="note">SLO: 99.5% of requests must complete within 3,000 ms over 28 days. Error budget: 0.5%.</div></main></body></html>''')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.substitute(
        title=html.escape(config["title"]), source=html.escape(str(log_path)), minutes=config["time_range_minutes"], refresh=config["refresh_seconds"],
        start=start.strftime("%Y-%m-%d %H:%M"), end=end.strftime("%Y-%m-%d %H:%M"), records=len(records), responses=len(responses), cards="".join(card_html)
    ), encoding="utf-8")
    print(f"Dashboard written to {output_path}")
    print(f"Window: {start.isoformat()} to {end.isoformat()} | records={len(records)} responses={len(responses)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the six-panel runtime dashboard from JSONL logs.")
    parser.add_argument("--logs", type=Path, default=Path("data/logs.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("config/dashboard.yaml"))
    parser.add_argument("--output", type=Path, default=Path("submission/evidence/11-dashboard-overview.html"))
    args = parser.parse_args()
    render(args.logs, args.config, args.output)


if __name__ == "__main__":
    main()