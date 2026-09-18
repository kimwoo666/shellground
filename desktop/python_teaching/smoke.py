"""Deployment proof: run the bundled interpreter as a child, not build Python."""
def main():
    import sys
    from .course import lesson_by_key
    from .engine import PythonEngine
    from .values import grade_snapshot
    engine=PythonEngine(timeout=20)
    try:
        tasks=[('np_elementwise',0),('pd_csv',2),('plot_save',0),('plot_normal',1),
               ('py_module_file',1),('sns_relationship',1),('sk_evaluation',2),
               ('pd_weather_audit',2),('pd_series_charts',1)]
        for key,variant in tasks:
            problem=lesson_by_key(key).problems[variant]
            engine.start(problem.initial,problem.files)
            if getattr(sys, 'frozen', False):
                proof=engine.execute("import sys\nworker_bundle = sys._MEIPASS")
                if not proof['ok']:raise RuntimeError(proof)
                actual=engine.inspect(['worker_bundle'])['values']['worker_bundle']
                if actual!=sys._MEIPASS:raise RuntimeError('Worker unpacked a second application bundle')
            result=engine.execute(problem.solution)
            if not result['ok']:raise RuntimeError((key,result))
            observed=engine.inspect(problem.targets,problem.probes)
            grade=grade_snapshot(observed['values'],problem.checks)
            if not grade['passed']:raise RuntimeError((key,grade))
        print(f'Python packaged-worker self-test: {len(tasks)} real scientific/file/module tasks passed')
        return 0
    finally:engine.close()
