import doctest

import k3git


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(k3git))
    return tests
