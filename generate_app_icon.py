from pathlib import Path

from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parent
    source = root / "static" / "app-icon.png"
    target = root / "static" / "app-icon.ico"

    if not source.exists():
        raise SystemExit(f"Missing source icon: {source}")

    image = Image.open(source).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    image.save(target, format="ICO", sizes=sizes)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
