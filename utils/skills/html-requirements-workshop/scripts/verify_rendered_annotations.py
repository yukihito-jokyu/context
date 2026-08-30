#!/usr/bin/env python3
"""Verify DOM-anchored annotation geometry in a headless Chromium browser."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote


DEFAULT_VIEWPORTS = ((1568, 784), (1280, 800), (1024, 768))
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--screenshot-dir", type=Path)
    parser.add_argument("--chrome", type=Path)
    parser.add_argument("--test-target", help="data-review-target key to select during browser verification")
    parser.add_argument("--test-selector", help="CSS selector inside data-ai-content to select during verification")
    parser.add_argument("--expect-selected-tag", help="expected semantic DOM tag after click target resolution")
    return parser.parse_args()


def find_chrome(explicit: Path | None) -> str:
    if explicit is not None:
        path = explicit.expanduser().resolve(strict=True)
        return str(path)
    for candidate in CHROME_CANDIDATES:
        if candidate.startswith("/") and Path(candidate).is_file():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SystemExit("Chrome or Chromium was not found; pass --chrome explicitly")


def stop_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        return process.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            return process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return process.communicate()


def verify_viewport(
    chrome: str,
    mock_path: Path,
    width: int,
    height: int,
    expected_count: int,
    expected_screen_detail_count: int,
    screenshot_dir: Path | None,
    test_target: str | None,
    test_selector: str | None,
    expected_tag: str | None,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="html-workshop-browser-") as profile:
        command = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--disable-background-networking",
            "--no-first-run",
            "--no-sandbox",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            "--virtual-time-budget=1200",
            "--dump-dom",
        ]
        screenshot_path: Path | None = None
        if screenshot_dir is not None:
            screenshot_path = screenshot_dir / f"annotations-{width}x{height}.png"
            command.append(f"--screenshot={screenshot_path}")
        mock_url = mock_path.as_uri()
        if test_target:
            mock_url += f"?review_test_target={quote(test_target)}&review_test_reuse=1&review_test_hit=1&review_test_scroll=1"
        elif test_selector:
            mock_url += f"?review_test_selector={quote(test_selector)}&review_test_reuse=1&review_test_hit=1&review_test_scroll=1"
        mock_url += ("&" if "?" in mock_url else "?") + "screen_detail_test=1"
        command.append(mock_url)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        stdout, stderr = stop_process(process)
    alignment = re.search(r'data-annotation-alignment="([^"]+)"', stdout)
    count = re.search(r'data-annotation-count="(\d+)"', stdout)
    errors = re.search(r'data-annotation-errors="(\d+)"', stdout)
    unapproved_nested_scrolls = re.search(r'data-unapproved-nested-scroll-count="(\d+)"', stdout)
    allowed_nested_scrolls = re.search(r'data-allowed-nested-scroll-count="(\d+)"', stdout)
    scroll_tested = re.search(r'data-scroll-tested="([^"]+)"', stdout)
    scroll_alignment = re.search(r'data-scroll-alignment="([^"]+)"', stdout)
    scroll_surface = re.search(r'data-scroll-surface="([^"]+)"', stdout)
    selection_number = re.search(r'data-dom-selection-number="(\d+)"', stdout)
    number_reuse = re.search(r'data-number-reuse="([^"]+)"', stdout)
    number_order = re.search(r'data-number-order="([^"]+)"', stdout)
    selection_kind = re.search(r'data-dom-selection-kind="([^"]+)"', stdout)
    selection_padding = re.search(r'data-dom-selection-padding="([^"]+)"', stdout)
    selection_tag = re.search(r'data-dom-selection-tag="([^"]+)"', stdout)
    selection_selector = re.search(r'data-dom-selection-selector="([^"]+)"', stdout)
    fixed_annotation_hit_test = re.search(r'data-fixed-annotation-hit-test="([^"]+)"', stdout)
    dom_annotation_hit_test = re.search(r'data-dom-annotation-hit-test="([^"]+)"', stdout)
    number_badge_hit_test = re.search(r'data-number-badge-hit-test="([^"]+)"', stdout)
    annotation_mode_number_pass_through = re.search(r'data-annotation-mode-number-pass-through="([^"]+)"', stdout)
    screen_detail_tested = re.search(r'data-screen-detail-tested="([^"]+)"', stdout)
    screen_detail_count = re.search(r'data-screen-detail-count="(\d+)"', stdout)
    screen_detail_alignment = re.search(r'data-screen-detail-alignment="([^"]+)"', stdout)
    screen_detail_checks = {
        name: re.search(rf'data-screen-detail-{name}="([^"]+)"', stdout)
        for name in (
            "number-order",
            "frame-order",
            "point-blue",
            "red",
            "pointer-pass",
            "annotate-hidden",
            "point-hidden",
            "hide",
            "restore",
            "first-expanded",
            "feedback",
            "return-isolation",
        )
    }
    result = {
        "viewport": f"{width}x{height}",
        "alignment": alignment.group(1) if alignment else "missing",
        "annotation_count": int(count.group(1)) if count else -1,
        "expected_annotation_count": expected_count,
        "annotation_errors": int(errors.group(1)) if errors else -1,
        "unapproved_nested_scroll_count": int(unapproved_nested_scrolls.group(1)) if unapproved_nested_scrolls else -1,
        "allowed_nested_scroll_count": int(allowed_nested_scrolls.group(1)) if allowed_nested_scrolls else -1,
        "scroll_tested": scroll_tested.group(1) == "true" if scroll_tested else False,
        "scroll_alignment": scroll_alignment.group(1) if scroll_alignment else "missing",
        "scroll_surface": scroll_surface.group(1) if scroll_surface else "missing",
        "dom_selection_tested": test_target is not None or test_selector is not None,
        "dom_selection_number": int(selection_number.group(1)) if selection_number else -1,
        "number_reuse": number_reuse.group(1) == "true" if number_reuse else False,
        "number_order": number_order.group(1) == "true" if number_order else False,
        "dom_selection_kind": selection_kind.group(1) if selection_kind else "missing",
        "dom_selection_padding": float(selection_padding.group(1)) if selection_padding else -1,
        "dom_selection_tag": selection_tag.group(1) if selection_tag else "missing",
        "dom_selection_selector": selection_selector.group(1) if selection_selector else "missing",
        "fixed_annotation_hit_test": fixed_annotation_hit_test.group(1) == "true" if fixed_annotation_hit_test else False,
        "dom_annotation_hit_test": dom_annotation_hit_test.group(1) == "true" if dom_annotation_hit_test else False,
        "number_badge_hit_test": number_badge_hit_test.group(1) == "true" if number_badge_hit_test else False,
        "annotation_mode_number_pass_through": annotation_mode_number_pass_through.group(1) == "true" if annotation_mode_number_pass_through else False,
        "screen_detail_tested": screen_detail_tested.group(1) == "true" if screen_detail_tested else False,
        "screen_detail_count": int(screen_detail_count.group(1)) if screen_detail_count else -1,
        "expected_screen_detail_count": expected_screen_detail_count,
        "screen_detail_alignment": screen_detail_alignment.group(1) if screen_detail_alignment else "missing",
        **{
            f"screen_detail_{name.replace('-', '_')}": match.group(1) == "true" if match else False
            for name, match in screen_detail_checks.items()
        },
        "browser_error": stderr.strip()[-800:] if not alignment else "",
        "screenshot": str(screenshot_path) if screenshot_path else None,
    }
    result["valid"] = (
        result["alignment"] == "valid"
        and result["annotation_count"] == expected_count
        and result["annotation_errors"] == 0
        and result["unapproved_nested_scroll_count"] == 0
        and result["allowed_nested_scroll_count"] >= 0
        and (test_target is None and test_selector is None or result["scroll_tested"])
        and (test_target is None and test_selector is None or result["scroll_alignment"] == "valid")
        and (test_target is None and test_selector is None or result["number_reuse"])
        and (test_target is None and test_selector is None or result["number_order"])
        and (test_target is None and test_selector is None or result["dom_selection_kind"] == "dom_annotation")
        and (test_target is None and test_selector is None or result["dom_selection_padding"] == 0)
        and (test_target is None and test_selector is None or result["fixed_annotation_hit_test"])
        and (test_target is None and test_selector is None or result["dom_annotation_hit_test"])
        and (test_target is None and test_selector is None or result["number_badge_hit_test"])
        and (test_target is None and test_selector is None or result["annotation_mode_number_pass_through"])
        and (expected_tag is None or result["dom_selection_tag"] == expected_tag)
        and result["screen_detail_tested"]
        and result["screen_detail_count"] == expected_screen_detail_count
        and result["screen_detail_alignment"] == "valid"
        and all(
            result[f"screen_detail_{name.replace('-', '_')}"]
            for name in screen_detail_checks
        )
    )
    return result


def main() -> None:
    args = parse_args()
    run = args.run.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"Refusing to overwrite: {output}")
    mockups = sorted((run / "mockups").glob("*.html")) if (run / "mockups").is_dir() else []
    if len(mockups) != 1:
        raise SystemExit("run must contain exactly one mock HTML")
    screenshot_dir = args.screenshot_dir.resolve() if args.screenshot_dir else None
    if screenshot_dir is not None:
        if screenshot_dir.exists() and any(screenshot_dir.iterdir()):
            raise SystemExit(f"Refusing to write into non-empty screenshot directory: {screenshot_dir}")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome(args.chrome)
    source = mockups[0].read_text(encoding="utf-8")
    fixed_count = len(re.findall(r'data-target-key="[a-z0-9-]+"', source))
    screen_detail_count = len(re.findall(r'data-screen-detail-number="\d+"', source))
    target_keys = re.findall(r'data-review-target="([a-z0-9-]+)"', source)
    if args.test_target and args.test_selector:
        raise SystemExit("pass either --test-target or --test-selector, not both")
    test_selector = args.test_selector
    test_target = args.test_target or (None if test_selector else (target_keys[0] if target_keys else None))
    if test_target is not None and test_target not in target_keys:
        raise SystemExit(f"test target was not found exactly once: {test_target}")
    expected_count = fixed_count + (1 if test_target or test_selector else 0)
    results = [
        verify_viewport(
            chrome,
            mockups[0],
            width,
            height,
            expected_count,
            screen_detail_count,
            screenshot_dir,
            test_target,
            test_selector,
            args.expect_selected_tag,
        )
        for width, height in DEFAULT_VIEWPORTS
    ]
    report = {
        "valid": all(item["valid"] for item in results),
        "mock": str(mockups[0]),
        "tested_dom_target": test_target,
        "tested_dom_selector": test_selector,
        "expected_selected_tag": args.expect_selected_tag,
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
