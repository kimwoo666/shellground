"""Explicitly authored practical course; adding units never grants completion."""
from functools import lru_cache


@lru_cache(maxsize=1)
def lessons():
    from .basics_course import lessons as basics
    from .foundations_course import lessons as foundations
    from .numpy_course import lessons as numpy
    from .numpy_advanced_course import lessons as numpy_advanced
    from .plot_course import lessons as plots
    from .pandas_course import lessons as pandas
    from .sources import audited
    from .integration_course import insertions
    extra=insertions()
    from .timing_course import lesson as timing
    extra['np_vectorize']=timing()
    course=[]
    for unit in basics() + foundations() + numpy() + numpy_advanced() + plots() + pandas():
        course.append(audited(unit))
        if unit.key in extra: course.append(audited(extra[unit.key]))
    from .review_course import insert_reviews
    from .library_course import lessons as libraries
    from .coverage_course import lessons as coverage
    # These are explicitly marked supplements, not APIs attributed to the PDFs.
    return insert_reviews(tuple(course)) + libraries() + coverage()


def lesson_by_key(key):
    return next(u for u in lessons() if u.key == key)
