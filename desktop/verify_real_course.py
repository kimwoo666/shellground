"""Checkpointed course acceptance in one app-owned Linux VM, never host Bash.

This driver types into a real PTY so cd, exports, job control and nano behave
as they do for a learner. Selection is explicit; a partial report is not full
course proof. Completed evidence is reused only for an identical source hash.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import queue
import re
import time
from course_topics import topic_of
from mode_curriculum import curriculum
from missions import make_mission
from real_course_checks import make_review
from real_lessons import adapt_real_mission
from real_vm import RealEngine


def fingerprint():
    root=Path(__file__).parent;digest=hashlib.sha256()
    names={'missions.py','practice.py','practice_variants.py','real_lessons.py','real_vm.py',
           'mode_curriculum.py','course_topics.py','checkpoints.py','real_course_checks.py'}
    paths={root/name for name in names if (root/name).exists()}
    for pattern in ('*_lessons.py','*_course.py','*_guides.py','guest/*.py','lab/*.py'):
        paths.update(p for p in root.glob(pattern) if not p.name.startswith('test_'))
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    return digest.hexdigest()


class Driver:
    def __init__(self,engine):self.engine=engine;self.terminal=None;self.mission=None
    def send(self,text):
        self.engine.channel.send(dict(action='input',session=self.terminal.sid,
                                      data=base64.b64encode(text.encode()).decode()))
    def prompt(self,timeout=40):
        output=b'';deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:line=self.terminal.queue.get(timeout=.2)
            except queue.Empty:continue
            if line is None:raise RuntimeError('PTY closed before prompt')
            data=base64.b64decode(json.loads(line)['output']);output+=data;self.engine.observe_output(data)
            clean=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',''.encode(),output)
            if re.search(rb'learner@lab:[^\r\n]*\$ ',clean):return
        raise TimeoutError('Bash prompt timeout: '+output.decode(errors='replace')[-1800:])
    def prepare(self,mission):
        self.mission=adapt_real_mission(mission)
        self.engine.start(self.mission);self.terminal=self.engine.open_terminal(self.mission);self.prompt()
    def solve(self):
        for command in self.mission.solution.splitlines():
            if not command or command.startswith('#'):continue
            if command.startswith('nano '):
                self.send(command+'\r');time.sleep(.25)
                if self.mission.kind=='edit' and any('reviewed=yes' in goal.get('text','') for goal in self.mission.review.get('goals',[])):
                    # The second application task preserves an owner line and
                    # appends a review marker; it is not the one-line example.
                    self.send('\x0bstatus=ready\r\x1b/reviewed=yes\x0f')
                else:self.send('\x0bstatus=ready\x0f')
                time.sleep(.15)
                self.send('\r');time.sleep(.15);self.send('\x18')
            else:
                # Same actual tools/options; answer apt's confirmation ahead
                # of time and use a shorter Docker stop grace in automation.
                command=command.replace('sudo apt install tree','sudo apt install -y tree')
                command=command.replace('docker stop ','docker stop -t 1 ')
                self.send(command+'\r')
            self.prompt()
    def grade(self):return self.engine.rpc('grade',self.mission)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--topic',choices=['linux-docker'],default='linux-docker')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--keys',nargs='+',help='Explicit diagnostic subset; not full-course proof')
    args=parser.parse_args();units,reviews=curriculum('real')
    selected=[u for u in units if topic_of(u)!='ROS 2']
    if args.keys:selected=[u for u in selected if u.key in args.keys]
    cases=[(u.key+':'+str(v),lambda u=u,v=v:make_mission(u.key,7251,v)) for u in selected for v in range(3)]
    if not args.keys:cases += [(c.key,lambda c=c:make_review(c,7251)) for c in reviews if all(topic_of(u)!='ROS 2' for u in c.units)]
    stamp=fingerprint();report=dict(state='in_progress',source_fingerprint=stamp,topic=args.topic,
        expected=[key for key,_ in cases],passed={},failures={})
    if args.resume and args.report.is_file():
        prior=json.loads(args.report.read_text())
        if prior.get('source_fingerprint')!=stamp or prior.get('expected')!=report['expected']:
            raise RuntimeError('Source/selection changed; use a new report instead of reusing stale proof')
        report['passed']=prior['passed']
    def checkpoint():
        args.report.parent.mkdir(parents=True,exist_ok=True);temporary=args.report.with_suffix('.tmp')
        temporary.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');temporary.replace(args.report)
    engine=RealEngine(args.runtime);driver=Driver(engine);started=time.monotonic();current=None
    try:
        for key,factory in cases:
            if key in report['passed']:continue
            current=key;case_started=time.monotonic();driver.prepare(factory())
            if driver.grade()['passed']:raise AssertionError('Initial fixture already passes: '+key)
            driver.solve();result=driver.grade()
            if not result['passed']:
                if driver.mission.kind=='edit':
                    observed=engine.channel.request('exec',root=False,cwd=driver.mission.start,
                        argv=['python3','-c','from pathlib import Path; print(repr(Path("note.txt").read_text()))'])
                    result['observed_file']=base64.b64decode(observed['out']).decode()
                raise AssertionError(result)
            report['passed'][key]=dict(seconds=round(time.monotonic()-case_started,2))
            checkpoint();print('REAL_COURSE_PASS '+key,flush=True)
        report['state']='complete'
    except BaseException as error:
        report['state']='failed';report['failures'][str(current)]=str(error)[-8000:];raise
    finally:
        process,session=engine.process,engine.session_dir;engine.close()
        report.update(seconds_this_run=round(time.monotonic()-started,2),
            vm_stopped=process is None or process.poll() is not None,overlay_removed=session is None or not session.exists())
        checkpoint();print(json.dumps({k:v for k,v in report.items() if k not in ('passed','expected')})+
            f' passed={len(report["passed"])}/{len(cases)}',flush=True)


if __name__=='__main__':main()
