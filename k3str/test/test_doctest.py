import doctest
import k3str


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(k3str))
    return tests
