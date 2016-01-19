#!/usr/bin/python3

import sys

from pocketlint import PocketLintConfig, PocketLinter

if __name__ == "__main__":
    conf = PocketLintConfig()
    linter = PocketLinter(conf)
    rc = linter.run()
    sys.exit(rc)
