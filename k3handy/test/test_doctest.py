import doctest

import k3handy


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(k3handy))
    return tests
