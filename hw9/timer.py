import time


def timer(fun):
    def wrapper(*args, **kwargs):
        start = time.time()
        fun(*args, **kwargs)
        time_fun = time.time() - start
        print('time %s %s' % (fun.__name__, time_fun))

    return wrapper