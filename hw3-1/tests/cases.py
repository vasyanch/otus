import functools


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as e:
                    print '\nTest --> {0}\nthis case: ({1}) is broken!'.format(f.__name__, c)
                    raise e
        return wrapper
    return decorator
