"""Build-time export; desktop and Android share the same lesson definitions."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
from python_teaching.course import lessons


def export(path):
    units=[]
    for unit in lessons():
        data=asdict(unit)
        data['learning_steps']=unit.learning_steps
        for problem, exported in zip(unit.problems, data['problems']):
            exported['display_initial']=problem.prepared_code
        for step, exported in zip(unit.guided_steps, data['guided_steps']):
            exported['practice']['display_initial']=step.practice.prepared_code
        units.append(data)
    quizzes=json.loads((Path(__file__).parent/'python_teaching/quiz_bank.json').read_text(encoding='utf-8'))
    cards=json.loads((Path(__file__).parent/'python_teaching/concept_cards.json').read_text(encoding='utf-8'))['cards']
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'schema':1,'lessons':units,'quizzes':quizzes['questions'],'concept_cards':cards},ensure_ascii=False),encoding='utf-8')
    print(f'Exported {len(units)} lessons and {len(quizzes["questions"])} quizzes: {target}')


if __name__=='__main__': export(sys.argv[1])
