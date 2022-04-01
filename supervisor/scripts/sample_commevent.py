#!/usr/local/bin/env python3
# -*-  coding:utf-8 -*-

import sys
import time


def write_stdout(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def main(sleep):
    while 1:
        write_stdout('<!--XSUPERVISOR:BEGIN-->')
        write_stdout('the data')
        write_stdout('<!--XSUPERVISOR:END-->')
        time.sleep(sleep)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(float(sys.argv[1]))
    else:
        main(1)

