"""Related practice navigation; never execution or completion equivalence."""
import json
from engine import resource_path
from .course import lessons
from conda_teaching.engine import course as conda_course


def resolve_target(target):
    if not isinstance(target,dict):raise ValueError('Invalid related practice target')
    mode=target.get('course');key=target.get('unit_key');variant=target.get('problem_index')
    if mode not in ('python','conda','notebook') or type(variant) is not int:
        raise ValueError('Invalid related practice target')
    if mode=='notebook':
        from notebook_teaching.course import lessons as notebook_lessons
        units=notebook_lessons()
    else:units=lessons() if mode=='python' else conda_course()['units']
    index=next((i for i,u in enumerate(units) if (u.key if mode=='python' else u['key'])==key),None)
    if index is None:raise ValueError('Related practice no longer exists: '+str(key))
    unit=units[index];problems=unit.problems if mode=='python' else unit['problems']
    if variant not in range(len(problems)) or variant not in (0,1,2):raise ValueError('Invalid practice variant')
    title=unit.title if mode=='python' else unit['title']
    return dict(course=mode,unit_key=key,problem_index=variant,index=index,title=title,
                phase=('example','practice1','practice2')[variant])


def load_links():
    source=json.loads(resource_path('python_teaching/quiz_practice_links.json').read_text(encoding='utf-8'))
    questions=json.loads(resource_path('python_teaching/quiz_bank.json').read_text(encoding='utf-8'))['questions']
    if source.get('schema')!=1:raise ValueError('Invalid related practice mapping')
    result={}
    conda={unit['key']:unit for unit in conda_course()['units']}
    for link in source['links']:
        key=link['quiz_id']
        if key in result or link['completion_equivalence'] is not False:
            raise ValueError('Duplicate link or unsupported completion equivalence')
        targets=[]
        for target in link['targets']:
            indexes=target.get('problem_indexes')
            if indexes is None:
                problems=conda[target['unit_key']]['problems'];by_id={p['id']:i for i,p in enumerate(problems)}
                indexes=[by_id[value] for value in target['problem_ids']]
            for variant in indexes:
                targets.append(resolve_target(dict(course=target['course'],unit_key=target['unit_key'],problem_index=variant)))
        if bool(targets)!=(link['classification']=='related_practice'):
            raise ValueError('Only explicitly related or unmapped practices are supported')
        result[key]=dict(link,targets=targets)
    if set(result)!={q['id'] for q in questions}:raise ValueError('Quiz mapping must cover every question')
    return result
