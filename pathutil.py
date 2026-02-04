#!/usr/bin/env python3
#
#
# Copyright (c) 2018 Ryo Nakamura.
# All rights reserved.
#
# $Id: pathutil.py v1.3 2018/12/21 12:26:30 nakamura Exp $
#

import os
import re
import sys


class Path:
    def __init__(self, path, *paths):
        self.path = os.path.join(path, *paths)

    def __repr__(self):
        return self.path

    def __str__(self):
        return self.path

    def absolute(self):
        return os.path.realpath(self.path)

    def basename(self, *suffixes):
        base = os.path.basename(self.path)
        for suffix in suffixes:
            # FIXME: dirty hack... must distinguish ``str'' and ``regexp''
            suffix.replace(".", "\.")
            m = re.match(rf"^(.+){suffix}$", base)
            if m:
                base = m.group(1)
                break

        return base

    def children(self, regexp=""):
        children = []
        try:
            children = os.listdir(path=self.path)
        except:
            self.warn("children", self.path)

        if regexp:
            children = list(filter(lambda _: re.search(regexp, _), children))

        return [Path(self.path, _) for _ in children]

    def dirname(self, absolute=True):
        if absolute:
            # not looks like directory
            if not re.match("/+$", self.path):
                return os.path.dirname(self.path)
            else:
                return self.path

    def exists(self):
        return os.path.exists(self.path)

    def is_absolute(self):
        return os.path.isabs(self.path)

    def is_dir(self):
        return os.path.isdir(self.path)

    def is_file(self):
        return os.path.isfile(self.path)

    def is_relative(self):
        return not os.path.isabs(self.path)

    def move(self, dst):
        os.rename(self.path, dst)

    def slurp(self, encoding=None):
        return "\n".join(self.lines(encoding=encoding))

    def lines(self, encoding=None):
        lines = []
        with open(self.path, "r", encoding=encoding) as f:
            lines = f.readlines()
        for _ in range(0, len(lines)):
            lines[_] = lines[_].rstrip()
        return lines

    def spew(self, data, encoding=None):
        with open(self.path, "w", encoding=encoding) as f:
            for line in data:
                print(line, file=f)

    def warn(self, *args):
        print(args, file=sys.stderr)


def main():
    Path("/tmp/")

    print(Path("/tmp/1.pl").is_file())
    print(Path("/tmp/1.pl").is_dir())
    print(Path("/tmp/1.pl").exists())
    print(Path("/tmp/1.pl").is_absolute())

    print(Path("/tmp/apl.pl").basename(".pl"))


if __name__ == "__main__":
    main()
