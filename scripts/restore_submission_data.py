"""Restore the shareable frozen snapshot to the original ignored runtime path. No API."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    info = json.loads((ROOT / 'data/day6/snapshot.json').read_text(encoding='utf-8'))
    payload = (ROOT / info['submission_path']).read_bytes()
    expected = json.loads((ROOT / 'data/benchmark/evaluation_protocol.json').read_text(encoding='utf-8'))['inputs']['chunks_sha256']
    if hashlib.sha256(payload).hexdigest() != expected or expected != info['sha256']:
        raise SystemExit('Packaged snapshot checksum mismatch; nothing restored.')
    destination = ROOT / info['runtime_path']
    if destination.exists() and destination.read_bytes() != payload:
        raise SystemExit('Runtime data differs; refusing to overwrite it.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    print('Snapshot verified/restored:', info['runtime_path'], 'SHA256:', expected)

if __name__ == '__main__':
    main()
