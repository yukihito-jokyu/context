import argparse
import tomllib
from pathlib import Path

from .render import STYLES, render_song


def main() -> None:
    parser = argparse.ArgumentParser(description="設計図(TOML)からループBGMを書き出す")
    parser.add_argument("song", type=Path, help="設計図のパス (例: songs/sample.toml)")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"))
    parser.add_argument("--style", choices=sorted(STYLES), default="standard", help="鳴らし方")
    args = parser.parse_args()

    spec = tomllib.loads(args.song.read_text(encoding="utf-8"))
    name = args.song.stem if args.style == "standard" else f"{args.song.stem}_{args.style}"
    out_dir = args.output / name
    report = render_song(spec, out_dir, name, args.style)

    seam = "OK" if report.seam_jump <= report.seam_reference * 1.25 else "要確認"
    print(f"書き出し先 : {out_dir / (name + '.wav')}")
    print(f"長さ       : {report.seconds:.3f} 秒 ({report.samples} サンプル)")
    print(f"ラウドネス : {report.lufs:.1f} LUFS / ピーク {report.peak_db:.1f} dBFS")
    print(f"リミッター : 全サンプルの {report.limited_percent:.2f}% に作用")
    print(f"つなぎ目   : {seam} (段差 {report.seam_jump:.4f} / 曲中の小節境界の最大 {report.seam_reference:.4f})")
    print("パート別   : 平均 / ピーク (dBFS)")
    for part, (mean_db, peak_db) in report.stem_levels.items():
        print(f"  {part:20s} {mean_db:7.1f} / {peak_db:7.1f}")


if __name__ == "__main__":
    main()
