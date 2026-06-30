from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from io import StringIO
import json
import subprocess


@dataclass(frozen=True)
class GpuStatus:
    index: int
    name: str
    memory_total_mb: int
    memory_used_mb: int
    memory_free_mb: int
    utilization_gpu_pct: int

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


def parse_nvidia_smi_csv(text: str) -> list[GpuStatus]:
    rows: list[GpuStatus] = []
    reader = csv.reader(StringIO(text.strip()))
    for row in reader:
        if not row or len(row) < 6:
            continue
        index, name, total, used, free, util = [part.strip() for part in row[:6]]
        rows.append(
            GpuStatus(
                index=int(index),
                name=name,
                memory_total_mb=int(total),
                memory_used_mb=int(used),
                memory_free_mb=int(free),
                utilization_gpu_pct=int(util),
            )
        )
    return rows


def choose_gpu(
    rows: list[GpuStatus],
    *,
    min_free_mb: int = 20_000,
    max_used_mb: int = 70_000,
) -> GpuStatus | None:
    candidates = [
        row
        for row in rows
        if row.memory_free_mb >= min_free_mb and row.memory_used_mb <= max_used_mb
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: (row.memory_free_mb, -row.utilization_gpu_pct), reverse=True)[0]


def query_gpu_status() -> list[GpuStatus]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return parse_nvidia_smi_csv(completed.stdout)


def gpu_report(
    rows: list[GpuStatus],
    *,
    min_free_mb: int = 20_000,
    max_used_mb: int = 70_000,
) -> dict[str, object]:
    selected = choose_gpu(rows, min_free_mb=min_free_mb, max_used_mb=max_used_mb)
    return {
        "gpus": [row.to_dict() for row in rows],
        "selection_policy": {
            "min_free_mb": min_free_mb,
            "max_used_mb": max_used_mb,
        },
        "selected_gpu": selected.to_dict() if selected else None,
    }


def gpu_report_json(
    rows: list[GpuStatus],
    *,
    min_free_mb: int = 20_000,
    max_used_mb: int = 70_000,
) -> str:
    return json.dumps(gpu_report(rows, min_free_mb=min_free_mb, max_used_mb=max_used_mb), indent=2)
