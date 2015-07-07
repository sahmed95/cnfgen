#!/usrbin/env python

import unittest

from cnfformula import CNF
from cnfformula.utils.solver import is_satisfiable, have_satsolver

class TestCNFBase(unittest.TestCase):
    """Base class for the test suite.

    It just implements some additional asserting features like testing
    that two CNFs are actually the same.
    """
    def assertCnfEqual(self,cnf1,cnf2):
        self.assertSetEqual(set(cnf1.variables()),set(cnf2.variables()))
        self.assertSetSetEqual(cnf1.clauses(),cnf2.clauses())

    def assertSetSetEqual(self,list1,list2):
        set1=set(frozenset(x) for x in list1)
        set2=set(frozenset(x) for x in list2)
        self.assertSetEqual(set1,set2)

    def assertSAT(self, formula):
        if have_satsolver():
            result, _ = is_satisfiable(formula)
            assert result

    def assertUNSAT(self, formula):
        if have_satsolver():
            result, _ = is_satisfiable(formula)
            assert not result