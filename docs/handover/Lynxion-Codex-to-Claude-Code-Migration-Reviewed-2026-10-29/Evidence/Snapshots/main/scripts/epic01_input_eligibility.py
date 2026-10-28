#!/usr/bin/env python3
"""Outcome-blind per-file eligibility disposition; never creates an eligible holdout."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):
            result.update(block)
    return result.hexdigest()


def classify(path, expected, origin, known_opened=False, quality=None):
    present=path.is_file()
    actual=digest(path) if present else None
    matches=actual==expected and present
    reasons=[]
    if not present:reasons.append('FILE_ABSENT')
    elif not matches:reasons.append('SOURCE_HASH_MISMATCH')
    if origin=='ORIGINAL_T01_INVENTORY':
        reasons.extend(['LINEAGE_UNVERIFIED_IN_SUPPLIED_INVENTORY',
                        'NO_PRECOMMITTED_INDEPENDENT_PARTITION_ATTESTATION_SUPPLIED'])
    if known_opened:reasons.append('RELATED_PRICE_COHORT_ALREADY_DEVELOPMENT_OPENED')
    if origin=='OBSERVED_VENDOR_COMPONENT':
        reasons.extend(['ONE_DAY_SELECTED_COMPONENT_SAMPLE','VENDOR_DISCONNECT_MARKERS_ABSENT'])
    if quality:
        reasons.extend(name.upper() for name in ('duplicates','gaps','invalid_ohlc','invalid_rows','out_of_order') if quality.get(name,0))
    role=('INVALID_OR_CHANGED_SOURCE' if not matches else
          'DEVELOPMENT_ONLY' if known_opened else 'UNQUALIFIED_RESEARCH_INPUT')
    return dict(file=str(path),origin=origin,expected_sha256=expected,actual_sha256=actual,
                source_hash_matched=matches,source_role=role,
                validation_admitted=False,holdout_admitted=False,
                economic_baseline_admitted=False,reason_codes=reasons)


def audit(inventory, primary, output):
    original=[json.loads(line) for line in inventory.read_text().splitlines() if line.strip()]
    if len(original)!=5150:raise ValueError('declared original population changed; re-scope explicitly')
    results=[classify(Path(r['file']),r['sha256'],'ORIGINAL_T01_INVENTORY',quality=r) for r in original]
    c06=primary/'data/research/c06/binance_futures_15m'
    manifest=json.loads((c06/'manifest.json').read_text())
    for symbol,meta in sorted(manifest['symbols'].items()):
        results.append(classify(c06/(symbol+'.csv'),meta['sha256'],'C06_PRIOR_RESEARCH',known_opened=True))
    root=primary/'data/research/epic01_mtf_maker/qualification_2026-10-28'
    acquisition=json.loads((root/'acquisition_manifest.json').read_text())
    for item in sorted(acquisition['raw_files'],key=lambda row:row['kind']):
        name=Path(item['filename'])
        if name.name!=str(name):raise ValueError('raw manifest filename must be a basename')
        results.append(classify(root/'raw'/name,item['sha256'],'OBSERVED_VENDOR_COMPONENT',known_opened=True))
    if len({r['file'] for r in results})!=len(results):raise ValueError('duplicate input identity')
    results.sort(key=lambda row:row['file'])
    content=''.join(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n' for row in results)
    output.mkdir(parents=True,exist_ok=True)
    with (output/'EPIC01_INPUT_ELIGIBILITY.jsonl').open('x') as sink:sink.write(content)
    summary=dict(scope='T01-S04 supplied 5150-file inventory plus six C06 inputs and two observed component files',
        inventory_path=str(inventory),inventory_sha256=digest(inventory),
        total_files=len(results),source_hashes_matched=sum(r['source_hash_matched'] for r in results),
        source_roles=dict(collections.Counter(r['source_role'] for r in results)),
        validation_files_admitted=0,holdout_files_admitted=0,economic_baseline_files_admitted=0,
        reason_counts=dict(collections.Counter(reason for row in results for reason in row['reason_codes'])),
        disposition='CLASSIFICATION_COMPLETE_NO_INDEPENDENT_PARTITION_ADMITTED',
        output_sha256=hashlib.sha256(content.encode()).hexdigest(),
        limits=['Eligibility decision for supplied evidence, not proof no other evidence could ever exist',
                'No prices/returns/strategy outcomes parsed or evaluated',
                'No new partitions, data repairs, OOS or economic admission created'])
    assert len(results)==5158 and not any(r['holdout_admitted'] or r['validation_admitted'] for r in results)
    with (output/'EPIC01_INPUT_ELIGIBILITY_SUMMARY.json').open('x') as sink:
        json.dump(summary,sink,indent=2);sink.write('\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,required=True)
    parser.add_argument('--primary',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.inventory,args.primary,args.output_dir),sort_keys=True))
