"""Recover a historical report from an exact completed terminal event, not rerun it."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def recover(transcript, process_id, destination):
    if destination.exists(): raise FileExistsError('Never overwrite an existing evidence report')
    found = []
    with transcript.open() as stream:
        for line in stream:
            record = json.loads(line); item = record.get('payload', {}).get('item', {})
            if (record.get('type') == 'event_msg' and item.get('type') == 'CommandExecution' and
                    item.get('process_id') == process_id and item.get('status') in ('completed', 'failed')):
                found.append((record, line.encode()))
    if len(found) != 1: raise RuntimeError('Need one exact completed terminal event')
    record, raw = found[0]; output = record['payload']['item']['aggregated_output']
    lines = output.splitlines()
    passed = [line.removeprefix('ROS_COURSE_PASS ') for line in lines if re.fullmatch(r'ROS_COURSE_PASS [a-z0-9_:-]+', line)]
    summaries = [(line, re.fullmatch(r'(\{.*\}) passed=(\d+)/(\d+)', line)) for line in lines]
    summaries = [(line, match) for line, match in summaries if match]
    if len(summaries) != 1: raise RuntimeError('One ROS terminal summary is required')
    summary, match = summaries[0]; report = json.loads(match[1])
    if len(passed) != len(set(passed)) or len(passed) != int(match[2]): raise RuntimeError('PASS count differs from terminal summary')
    if not report.get('source_fingerprint') or report.get('vm_stopped') is not True or report.get('overlay_removed') is not True:
        raise RuntimeError('Historical provenance or cleanup is missing')
    report.update(passed=passed, original_expected_count=int(match[3]),
                  scope='historical-ROS-report-recovered-from-completed-terminal-event-not-a-new-run',
                  recovered_from=dict(transcript=str(transcript), process_id=process_id,
                                      timestamp=record['timestamp'], ordinal=record['ordinal'],
                                      event_line_sha256=hashlib.sha256(raw).hexdigest(),
                                      terminal_excerpt='\n'.join('ROS_COURSE_PASS ' + key for key in passed) + '\n' + summary))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as stream: json.dump(report, stream, ensure_ascii=False, indent=2); stream.write('\n')
    return {key: report[key] for key in ('state', 'source_fingerprint', 'original_expected_count', 'vm_stopped', 'overlay_removed')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcript', type=Path); parser.add_argument('process_id'); parser.add_argument('destination', type=Path)
    args = parser.parse_args(); print(json.dumps(recover(args.transcript, args.process_id, args.destination)))
