"""Replay saved real answer/refusal/error traces without a database or API key."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['all', 'answer', 'refusal', 'error'], default='all')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'artifacts/demo/demo_cases.json').read_text(encoding='utf-8'))
    chunks = {c['id']: c for c in json.loads((ROOT / 'data/day6/chunks.json').read_text(encoding='utf-8'))}
    print(manifest['mode'])
    for name, entry in manifest['cases'].items():
        if args.case != 'all' and args.case != name:
            continue
        path = ROOT / entry['trace']
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise SystemExit('Trace checksum mismatch: ' + entry['trace'])
        trace = json.loads(raw)
        print('\nCASE:', name, '| status:', trace['status'])
        print('Question:', trace['question'])
        print('Answer:', trace.get('answer') or '(no answer; real request failed)')
        for cid in trace.get('citations', []):
            c = chunks[cid]
            print('Citation:', cid, '| source:', c['source'], '| physical PDF page:', c['page'])
        if trace.get('error'):
            print('Error:', json.dumps(trace['error'], ensure_ascii=False))
        print('Full trace:', entry['trace'])

if __name__ == '__main__':
    main()
