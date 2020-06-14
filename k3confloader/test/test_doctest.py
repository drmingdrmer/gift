import doctest

import k3confloader


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(k3confloader))
    return tests
