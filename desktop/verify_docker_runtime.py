"""Incremental actual verification of Docker 21–25 only; preserve each report."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import time
from real_vm import RealEngine
from verify_real_course import Driver
from docker_runtime_course import KEYS, make_mission, http_run

FILES = ('docker_runtime_course.py', 'guest/docker_runtime_lab.py', 'guest/docker_lab.py', 'guest/agent.py',
         'real_vm.py', 'missions.py', 'mode_curriculum.py', 'real_course_checks.py', 'learning_steps.py', 'verify_docker_runtime.py')


class RuntimeDriver(Driver):
    def command(self, text): self.send(text + '\r'); self.prompt()


def verify(runtime, destination, cases=None):
    if destination.exists(): raise FileExistsError('Previous proof must be preserved')
    valid = [key + ':' + str(v) for key in KEYS for v in range(3)] + ['docker_runtime_review:0']
    selected = valid if cases is None else cases
    if not selected or len(set(selected)) != len(selected) or set(selected) - set(valid): raise ValueError('Invalid explicit selection')
    root = Path(__file__).parent
    hashes = lambda: {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}
    report = dict(scope='new-docker-runtime-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[], source_hashes=hashes())
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True); tmp = destination.with_suffix('.tmp')
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); tmp.replace(destination)
    engine = RealEngine(runtime); driver = RuntimeDriver(engine); started = time.monotonic()
    def grade(expected):
        result = driver.grade()
        if result['passed'] is not expected or len(result['checks']) > 7: raise AssertionError(result)
    def remember(label): report['negative'].append(label); save()
    try:
        for case in selected:
            key, v = case.split(':'); v = int(v)
            driver.prepare(make_mission(key, 7251, v)); grade(False)
            name = driver.mission.review['name']; start = driver.mission.start
            driver.solve(); grade(True); report['passed'].append(case); save(); print('DOCKER_RUNTIME_PASS', case, flush=True)
            if case == 'docker_runtime_http:0':
                driver.command(f'docker rm -f {name}')
                driver.command(http_run(start, name, 47251, '0.0.0.0')); grade(False)
                driver.command(f'docker rm -f {name}')
                driver.command(http_run(start, name, 47251)); grade(True)
                remember('same_http_body_on_all_address_publication_rejected')
            elif case == 'docker_runtime_http:1':
                driver.command(f'docker rm -f {name}'); driver.command(http_run(start, name, 47251)); grade(False)
                remember('unnecessary_recreation_of_404_service_rejected')
            elif case == 'docker_runtime_stats:0':
                driver.command('cp stats.txt original-stats.txt')
                driver.command("sed 's@/ 32MiB@/ 512MiB@' original-stats.txt > stats.txt"); grade(False)
                driver.command('cp original-stats.txt stats.txt'); grade(True)
                remember('usage_limit_confusion_rejected_without_fixed_usage_target')
            elif case == 'docker_runtime_stats:2':
                driver.command('printf "0\\n" > memory-limit.txt'); grade(False)
                driver.command('printf "33554432\\n" > memory-limit.txt'); grade(True)
                remember('stopped_container_zero_limit_claim_rejected')
            elif case == 'docker_runtime_cpu:0':
                driver.command(f'docker update --cpus .25 {name}'); grade(False)
                driver.command(f'docker update --cpus .5 {name}'); grade(True)
                driver.command(f'docker rm -f {name}')
                driver.command(f'docker run -d --name {name} --network none --memory 32m --pids-limit 32 --cpu-quota 25000 --cpu-period 50000 localhost:5000/training/alpine:latest sleep 3600'); grade(True)
                remember('wrong_quota_rejected_and_equivalent_quota_period_accepted')
            elif case == 'docker_runtime_io_weight:0':
                driver.command(f'docker update --blkio-weight 600 {name}'); grade(False)
                driver.command(f'docker update --blkio-weight 300 {name}'); grade(True)
                driver.command(f'docker update --cpus .5 {name}'); grade(False)
                driver.command(f'docker update --cpus .25 {name}'); grade(True)
                remember('wrong_requested_weight_and_missing_required_cpu_limit_rejected')
            elif case == 'docker_runtime_io_weight:2':
                driver.command('printf "effect=600MB/s\\n" > effect.txt'); grade(False)
                driver.command('printf "effect=unmeasured\\n" > effect.txt'); grade(True)
                remember('weight_as_guaranteed_throughput_rejected')
            elif case == 'docker_runtime_safe_launcher:0':
                driver.command(f'docker rm {name}')
                driver.command("sed -i 's/exec docker run/exec docker create/' run-job.sh")
                driver.command(f'./run-job.sh "{start}/input/source notes.txt" "{start}/output" {name}'); grade(False)
                remember('created_never_executed_container_with_stale_correct_files_rejected')
            elif case == 'docker_runtime_safe_launcher:1':
                driver.command('cp run-job.sh good-launcher.sh')
                # Looks correct for the first paths but violates the reusable contract.
                driver.command(f"sed 's@src=$1,dst@src={start}/input/source notes.txt,dst@' good-launcher.sh > run-job.sh"); grade(False)
                driver.command('cp good-launcher.sh run-job.sh'); grade(True)
                remember('launcher_hardcoding_original_input_rejected_by_fresh_space_path')
        if hashes() != report['source_hashes']: raise AssertionError('Sources changed during actual execution')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-7000:]); raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k: v for k, v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True); parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cases', nargs='+'); args = parser.parse_args()
    verify(args.runtime, args.report, args.cases)
