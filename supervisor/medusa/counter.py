#!/usr/local/bin/env python3
# -*-  coding:utf-8 -*-

from supervisor.compat import long


class counter:
    """general-purpose counter"""

    def __init__ (self, initial_value=0):
        self.value = initial_value

    def increment (self, delta=1):
        result = self.value
        try:
            self.value = self.value + delta
        except OverflowError:
            self.value = long(self.value) + delta
        return result

    def decrement (self, delta=1):
        result = self.value
        try:
            self.value = self.value - delta
        except OverflowError:
            self.value = long(self.value) - delta
        return result

    def as_long (self):
        return long(self.value)

    def __nonzero__ (self):
        return self.value != 0

    __bool__ = __nonzero__

    def __repr__ (self):
        return '<counter value=%s at %x>' % (self.value, id(self))

    def __str__ (self):
        s = str(long(self.value))
        if s[-1:] == 'L':
            s = s[:-1]
        return s

