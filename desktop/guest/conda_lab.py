"""Conda course adapter to the real isolated guest process, not a CLI emulator."""
import base64
import json


class CondaLab:
    def __init__(self,agent):self.agent=agent;self.mission=None

    def call(self,action,payload):
        result=self.agent.run(['/opt/shellground/miniconda/bin/python','-I',
            '/opt/shellground/conda_runtime.py',action],json.dumps(payload).encode(),
            root=True,cwd='/tmp',timeout=115)
        if result['code']:raise RuntimeError(base64.b64decode(result['err']).decode(errors='replace'))
        return json.loads(base64.b64decode(result['out']))

    def prepare(self,mission):
        self.mission=mission
        return self.call('prepare',mission['problem'])

    def grade(self,mission,sid,answers):
        if mission!=self.mission:raise ValueError('Conda problem is not prepared')
        return self.call('grade',{'problem_id':mission['problem']['id'],'session':sid,
                                 'answers':answers,'probes':mission['probes']})
