#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(fun):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable
    '''
    return fun


def decorator(deco):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    def wrapper(fun):
        return update_wrapper(deco(fun), fun)
    update_wrapper(wrapper, deco)
    return wrapper


@decorator
def countcalls(fun):
    '''Decorator that counts calls made to the function decorated.'''
    def wrapper(*args, **kwargs):
        wrapper.calls = getattr(wrapper, 'calls', 0) + 1
        # print '{0} was called {1}-x'.format(fun.__name__, wrapper.calls)
        return fun(*args, **kwargs)
    return wrapper


@decorator
def memo(fun):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    cash = {}
    def wrapper(*args):
        update_wrapper(wrapper, fun)
        if args in cash:
            return cash[args]
        res = cash[args] = fun(*args)
        return res
    return wrapper


@decorator
def n_ary(fun):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def wrapper(x, *args):
        return x if not args else fun(x, wrapper(*args))
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

    @decorator
    def deco(fun):
        fun.depth = 0

        def wrapper(*args):
            print '{0} --> {1}({2})'.format(indent*fun.depth, fun.__name__, ','.join(map(repr, args)))
            fun.depth += 1
            res = fun(*args)
            fun.depth -=1
            print '{0}<-- {1}({2}) == {3}'.format(indent*fun.depth, fun.__name__, ','.join(map(repr, args)), res)
            return res
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
