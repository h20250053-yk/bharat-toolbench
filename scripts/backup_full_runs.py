"""Back up all new full-run, pilot and smoke files (+ analysis summaries, config and gold) into one tar.gz OUTSIDE the repo and verify it.

    python scripts/backup_full_runs.py --full-ts 20261124T105853Z --pilot-ts 20261124T102758Z [--out-dir ~/FreeModel/backups]

Reads only; never modifies the originals. Writes <out-dir>/bharat_full_runs_<UTC timestamp>.tar.gz and a SHA256SUMS file inside it, then re-opens the archive,
checks that every file is listed, and extracts a sample (the largest run file, a summary, a manifest and SHA256SUMS) to a temp dir comparing checksums.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import random
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(full_ts: str, pilot_ts: str, root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for pat in (f"runs/*_full_{full_ts}*", f"runs/full_phase_{full_ts}*", f"runs/*_pilot_{pilot_ts}*", f"runs/*_smoke_{pilot_ts}*", f"runs/pilot_phase_{pilot_ts}*",
                f"runs/*_ps_{pilot_ts}*", f"runs/*_ps_{full_ts}*"):
        files += [p for p in root.glob(pat) if p.is_file()]
    for pat in (f"analysis/results/*_full_{full_ts}", f"analysis/results/*_pilot_{pilot_ts}"):
        for d in root.glob(pat):
            files += [p for p in d.rglob("*") if p.is_file()]
    files += [root / "config" / "models.yaml", root / "config" / "benchmark.yaml", root / "benchmark" / "gold_labels.json", root / "benchmark" / "semantic_tasks.json"]
    files += sorted((root / "benchmark" / "languages").glob("*.jsonl"))
    return sorted({p for p in files if p.exists()})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--full-ts", required=True)
    ap.add_argument("--pilot-ts", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path.home() / "FreeModel" / "backups")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    files = collect(args.full_ts, args.pilot_ts, args.root)
    if not files:
        raise SystemExit("nothing to back up")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out_dir / f"bharat_full_runs_{stamp}.tar.gz"
    sums = {p.relative_to(args.root).as_posix(): sha256(p) for p in files}
    sumtext = "".join(f"{h}  {name}\n" for name, h in sums.items()).encode()
    with tarfile.open(out, "w:gz") as tar:
        for p in files:
            tar.add(p, arcname=p.relative_to(args.root).as_posix())
        info = tarfile.TarInfo("SHA256SUMS")
        info.size, info.mtime = len(sumtext), int(datetime.now(timezone.utc).timestamp())
        tar.addfile(info, io.BytesIO(sumtext))
    # ---- verify: the archive opens, lists every file, and a sample extracts with identical checksums
    with tarfile.open(out, "r:gz") as tar:
        names = set(tar.getnames())
        missing = [n for n in sums if n not in names]
        if missing or "SHA256SUMS" not in names:
            raise SystemExit(f"VERIFY FAILED: missing in archive: {missing[:5]}")
        big = max(sums, key=lambda n: (args.root / n).stat().st_size)
        sample = [big, "SHA256SUMS"] + random.Random(0).sample(sorted(sums), min(5, len(sums)))
        with tempfile.TemporaryDirectory() as td:
            for n in sample:
                tar.extract(n, td, filter="data")
                got = sha256(Path(td) / n)
                want = sums.get(n) or hashlib.sha256(sumtext).hexdigest()
                if got != want:
                    raise SystemExit(f"VERIFY FAILED: checksum differs for {n}")
    print(f"backup OK: {out} ({out.stat().st_size / 1e6:.1f} MB, {len(files)} files + SHA256SUMS); sample of {len(sample)} files re-extracted and checksummed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
