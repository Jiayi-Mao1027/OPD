from reconcile_opsd.gpu_utils import choose_gpu, gpu_report, parse_nvidia_smi_csv


def test_parse_nvidia_smi_csv():
    rows = parse_nvidia_smi_csv(
        "\n".join(
            [
                "0, NVIDIA H100 PCIe, 81559, 75315, 5680, 0",
                "1, NVIDIA H100 PCIe, 81559, 28329, 52666, 91",
            ]
        )
    )
    assert len(rows) == 2
    assert rows[0].index == 0
    assert rows[1].memory_free_mb == 52666


def test_choose_gpu_respects_memory_policy():
    rows = parse_nvidia_smi_csv(
        "\n".join(
            [
                "0, NVIDIA H100 PCIe, 81559, 75315, 5680, 0",
                "1, NVIDIA H100 PCIe, 81559, 28329, 52666, 91",
                "2, NVIDIA H100 PCIe, 81559, 61823, 19172, 69",
            ]
        )
    )
    selected = choose_gpu(rows, min_free_mb=20_000, max_used_mb=70_000)
    assert selected is not None
    assert selected.index == 1


def test_choose_gpu_returns_none_when_all_too_busy():
    rows = parse_nvidia_smi_csv("0, NVIDIA H100 PCIe, 81559, 75315, 5680, 0")
    assert choose_gpu(rows, min_free_mb=20_000, max_used_mb=70_000) is None


def test_gpu_report_includes_policy_and_selection():
    rows = parse_nvidia_smi_csv("1, NVIDIA H100 PCIe, 81559, 28329, 52666, 91")
    report = gpu_report(rows, min_free_mb=20_000, max_used_mb=70_000)
    assert report["selection_policy"]["min_free_mb"] == 20_000
    assert report["selected_gpu"]["index"] == 1
