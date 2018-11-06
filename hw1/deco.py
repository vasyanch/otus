#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper
from functools import wraps


def disable(fun):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    return fun


def decorator(fun):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    @wraps(fun)
    def wrapper(*args, **kwargs):
        res = fun(*args, **kwargs)
        return res

    return wrapper


def countcalls(fun):
    '''Decorator that counts calls made to the function decorated.'''
    
    @wraps(fun)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        res = fun(*args, **kwargs)
        # print '{0} was called {1}-x'.format(fun.__name__, wrapper.calls)
        return res
    wrapper.calls = 0
    return wrapper


def memo(fun):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    cash = {}
    @wraps(fun)
    def wrapper(*args):
        if args in cash:
            return cash[args]
        res = fun(*args)
        if hasattr(fun, 'calls'):
            wrapper.calls = fun.calls
        cash[args] = res
        return res
    
    return wrapper


def n_ary(fun):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def wrapper(*args):
        end = len(args)
        if end > 2:
            i = end - 3
            res = fun(args[end - 1], args[end - 2])
            while i >= 0:
                res = fun(args[i], res)
                i -= 1
            return res
        elif end == 2:
            return fun(args[0], args[1])
        else:
            return args[0]
    return wrapper


def trace(indent):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    
    def deco(fun):
        fun.depth = 0
        #@wraps(fun)
        def wrapper(n):
            print '{0} --> {1}({2})'.format(indent*fun.depth, fun.__name__, n)
            if n > 1:
                fun.depth += 1
            res = fun(n)
            if n > 1:
                fun.depth -=1
            print '{0}<-- {1}({2}) == {3}'.format(indent*fun.depth, fun.__name__, n, res)
            return res
        wrapper = update_wrapper(wrapper, fun)
        return wrapper
    return deco


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print foo(4, 3)
    print foo(4, 3, 2)
    print foo(4, 3)
    print "foo was called", foo.calls, "times"

    print bar(4, 3)
    print bar(4, 3, 2)
    print bar(4, 3, 2, 1)
    print "bar was called", bar.calls, "times"

    print fib.__doc__
    fib(3)
    print fib.calls, 'calls made'


if __name__ == '__main__':
    main()
