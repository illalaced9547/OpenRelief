"""Offline dataset and optional supervision preflight for the GPU handoff."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from .adapter import format_input, format_training
from .dataset import load_examples, assign_split, month_index


def validate(directory, annotations=None, require_complete=False):
    manifest = json.loads((directory / 'manifest.json').read_text())
    labels = {}
    if annotations:
        for row in map(json.loads, annotations.read_text().splitlines()):
            if row['sample_id'] in labels:
                raise ValueError('Duplicate annotation')
            labels[row['sample_id']] = row
    countries, coverage, totals = {}, Counter(), Counter()
    seen, train_ids = set(), set()
    names = None
    for split in ('train', 'validation', 'test'):
        examples = load_examples(directory, split)
        if len(examples) != manifest['counts'][split]:
            raise ValueError('Partition count mismatch')
        countries[split] = dict(Counter(e['input']['geography']['iso3'] for e in examples))
        for example in examples:
            sample, target = example['input'], example['target']
            sid = sample['sample_id']
            if sid in seen:
                raise ValueError('Duplicate sample ID')
            seen.add(sid)
            if split == 'train':
                train_ids.add(sid)
            if sample['dataset_version'] != manifest['dataset_version']:
                raise ValueError('Dataset version mismatch')
            cutoff = month_index(sample['cutoff'][:7])
            future = month_index(target['target_month'])
            if future - cutoff != manifest['config']['horizon_months'] or assign_split(cutoff, future, manifest['config']) != split:
                raise ValueError('Horizon or split leakage')
            current_names = [c['name'] for c in sample['channels']]
            if names is None:
                names = current_names
            if current_names != names or len(set(names)) != len(names):
                raise ValueError('Inconsistent channel schema')
            for channel in sample['channels']:
                if len(channel['values']) != manifest['config']['window_months'] or len(channel['availability_times']) != len(channel['values']):
                    raise ValueError('Channel shape mismatch')
                if any(month_index(m) >= cutoff for m in channel['months']):
                    raise ValueError('Input event month crosses configured lag')
                if channel['name'] == 'month_of_year' and channel['values'] != [month_index(m) % 12 + 1 for m in channel['months']]:
                    raise ValueError('Calendar encoding mismatch')
                coverage[channel['name']] += sum(v is not None for v in channel['values'])
                totals[channel['name']] += len(channel['values'])
            format_input(sample)
            if sid in labels:
                if split != 'train':
                    raise ValueError('Non-training annotation supplied')
                from .annotation import validate_annotation
                validate_annotation(labels[sid]['annotation'], example)
                format_training(example, '', labels[sid])
    if set(labels) - train_ids:
        raise ValueError('Unknown annotation ID')
    if require_complete and set(labels) != train_ids:
        raise ValueError(f'Complete annotation required: {len(labels)} / {len(train_ids)}')
    return {'dataset_version': manifest['dataset_version'], 'counts': manifest['counts'],
            'countries': countries, 'channels': names, 'channel_count': len(names),
            'coverage': {n: coverage[n] / totals[n] for n in names},
            'validated_annotations': len(labels), 'annotations_complete': set(labels) == train_ids,
            'integrity_and_temporal_checks': 'passed'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--require-complete-annotations', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('reports/dataset-validation.json'))
    args = parser.parse_args()
    result = validate(args.dataset, args.annotations, args.require_complete_annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
