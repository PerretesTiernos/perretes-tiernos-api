"""Export or verify the FastAPI OpenAPI specification at `openapi.json`."""

import argparse
import json
import sys
from pathlib import Path

from app.main import app


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or verify openapi.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that openapi.json matches the current FastAPI specification",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    output_path = root_dir / "openapi.json"
    expected_content = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not output_path.exists():
            print("ERROR: openapi.json does not exist.", file=sys.stderr)
            return 1
        current_content = output_path.read_text(encoding="utf-8")
        if json.loads(current_content) != json.loads(expected_content):
            print(
                "ERROR: openapi.json is out of sync with FastAPI routers/schemas. "
                "Run `python -m scripts.generate_openapi`.",
                file=sys.stderr,
            )
            return 1
        print("OK: openapi.json is up to date.")
        return 0

    output_path.write_text(expected_content, encoding="utf-8")
    print(f"Exported OpenAPI specification to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

