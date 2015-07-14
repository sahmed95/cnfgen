#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Formula families useful in proof complexity

Copyright (C) 2012, 2013, 2014, 2015  Massimo Lauria <lauria@kth.se>
https://github.com/MassimoLauria/cnfgen.git
"""

from __future__ import print_function
from ..cnf import CNF

# internal methods
from ..graphs import enumerate_vertices,is_dag
from ..cnf    import parity_constraint
from ..cnf    import equal_to_constraint
from ..cnf    import less_than_constraint
from ..cnf    import less_or_equal_constraint
from ..cnf    import greater_than_constraint
from ..cnf    import greater_or_equal_constraint
from ..cnf    import loose_minority_constraint
from ..cnf    import loose_majority_constraint

# removes duplicates from list maintaining order
import collections

def unify_list(x):
    """Remove duplicates while maintaining the order."""
    x=collections.OrderedDict.fromkeys(x)
    return x.keys()


# Import formulas for library access
from .pigeonhole import PigeonholePrinciple,GraphPigeonholePrinciple



__all__ = ["PigeonholePrinciple",
           "GraphPigeonholePrinciple",
           "PebblingFormula",
           "StoneFormula",
           "OrderingPrinciple",
           "GraphOrderingPrinciple",
           "GraphIsomorphism",
           "GraphAutomorphism",
           "RamseyNumber",
           "SubsetCardinalityFormula",
           "TseitinFormula",
           "ParityPrinciple",
           "MarkstromFormula",
           "PerfectMatchingPrinciple",
           "CountingPrinciple",
           "ColoringFormula",
           "SubgraphFormula",
           "RandomKCNF"]

import sys
from textwrap import dedent
from itertools import product,permutations
from itertools import combinations,combinations_with_replacement


# Network X is used to produce graph based formulas
try:
    import networkx
except ImportError:
    print("ERROR: Missing 'networkx' library: no support for graph based formulas.",
          file=sys.stderr)
    exit(-1)




class FormulaFamilyHelper(object):
    """Command Line helper for formula families

    For every formula family there should be a subclass.
    """
    description=None
    name=None

    @staticmethod
    def build_cnf(args):
        pass

    @staticmethod
    def setup_command_line(parser):
        pass

    

def SubsetCardinalityFormula(B):
    r"""SubsetCardinalityFormula

    Consider a bipartite graph :math:`B`. The CNF claims that at least half
    of the edges incident to each of the vertices on left side of :math:`B`
    must be zero, while at least half of the edges incident to each
    vertex on the left side must be one.

    Variants of these formula on specific families of bipartite graphs
    have been studied in [1]_, [2]_ and [3]_, and turned out to be
    difficult for resolution based SAT-solvers.

    Each variable of the formula is denoted as :math:`x_{i,j}` where
    :math:`\{i,j\}` is an edge of the bipartite graph. The clauses of
    the CNF encode the following constraints on the edge variables.

    For every left vertex i with neighborhood :math:`\Gamma(i)`

    .. math::
         
         \sum_{j \in \Gamma(i)} x_{i,j} \leq \frac{|\Gamma(i)|}{2}

    For every right vertex j with neighborhood :math:`\Gamma(j)`

    .. math::
         
         \sum_{i \in \Gamma(j)} x_{i,j} \geq \frac{|\Gamma(i)|}{2}.

    Parameters
    ----------
    B : networkx.Graph
        the graph vertices must have the 'bipartite' attribute
        set. Left vertices must have it set to 0 and the right ones to 1.
        Any vertex without the attribute is ignored.

    Returns
    -------
    A CNF object

    References
    ----------
    .. [1] Mladen Miksa and Jakob Nordstrom
           Long proofs of (seemingly) simple formulas
           Theory and Applications of Satisfiability Testing--SAT 2014 (2014)
    .. [2] Ivor Spence
           sgen1: A generator of small but difficult satisfiability benchmarks
           Journal of Experimental Algorithmics (2010)
    .. [3] Allen Van Gelder and Ivor Spence
           Zero-One Designs Produce Small Hard SAT Instances
           Theory and Applications of Satisfiability Testing--SAT 2010(2010)

    """
    Left  =  [v for v in B.nodes() if B.node[v]["bipartite"]==0]
    Right =  [v for v in B.nodes() if B.node[v]["bipartite"]==1]
            
    ssc=CNF()
    ssc.header="Subset cardinality formula for graph {0}\n".format(B.name)

    def var_name(u,v):
        """Compute the variable names."""
        if u<=v:
            return 'x_{{{0},{1}}}'.format(u,v)
        else:
            return 'x_{{{0},{1}}}'.format(v,u)
    
    for u in Left:
        edge_vars = [ var_name(*e) for e in B.edges(u) ]
        for cls in loose_minority_constraint(edge_vars):
            ssc.add_clause(cls)

    for v in Right:
        edge_vars = [ var_name(*e) for e in B.edges(v) ]
        for cls in loose_majority_constraint(edge_vars):
            ssc.add_clause(cls)
    
    return ssc

def PebblingFormula(digraph):
    """Pebbling formula

    Build a pebbling formula from the directed graph. If the graph has
    an `ordered_vertices` attribute, then it is used to enumerate the
    vertices (and the corresponding variables).

    Arguments:
    - `digraph`: directed acyclic graph.
    """
    if not is_dag(digraph):
        raise ValueError("Pebbling formula is defined only for directed acyclic graphs")

    peb=CNF()

    if hasattr(digraph,'name'):
        peb.header="Pebbling formula of: "+digraph.name+"\n\n"+peb.header
    else:
        peb.header="Pebbling formula\n\n"+peb.header

    # add variables in the appropriate order
    vertices=enumerate_vertices(digraph)
    position=dict((v,i) for (i,v) in enumerate(vertices))

    for v in vertices:
        peb.add_variable(v,description="There is a pebble on vertex ${}$".format(v))

    # add the clauses
    for v in vertices:

        # If predecessors are pebbled the vertex must be pebbled
        pred=sorted(digraph.predecessors(v),key=lambda x:position[x])
        peb.add_clause([(False,p) for p in pred]+[(True,v)])

        if digraph.out_degree(v)==0: #the sink
            peb.add_clause([(False,v)])

    return peb

def StoneFormula(D,nstones):
    """Stones formulas

    The stone formulas have been introduced in [2]_ and generalized in
    [1]_. They are one of the classic examples that separate regular
    resolutions from general resolution [1]_.

    A \"Stones formula\" from a directed acyclic graph :math:`D`
    claims that each vertex of the graph is associated with one on
    :math:`s` stones (not necessarily in an injective way).
    In particular for each vertex :math:`v` in :math:`V(D)` and each
    stone :math:`j` we have a variable :math:`P_{v,j}` that claims
    that stone :math:`j` is associated to vertex :math:`v`.

    Each stone can be either red or blue, and not both.
    The propositional variable :math:`R_j` if true when the stone
    :math:`j` is red and false otherwise.

    The clauses of the formula encode the following constraints.
    If a stone is on a source vertex (i.e. a vertex with no incoming
    edges), then it must be red. If all stones on the predecessors of
    a vertex are red, then the stone of the vertex itself must be red.

    The formula furthermore enforces that the stones on the sinks
    (i.e. vertices with no outgoing edges) are blue.

    .. note:: The exact formula structure depends by the graph and on
              its topological order, which is determined by the
              ``enumerate_vertices(D)``.

    Parameters
    ----------
    D : a directed acyclic graph
        it should be a directed acyclic graph.
    nstones : int
       the number of stones.

    Raises
    ------
    ValueError
       if :math:`D` is not a directed acyclic graph
    
    ValueError
       if the number of stones is negative

    References
    ----------
    .. [1] M. Alekhnovich, J. Johannsen, T. Pitassi and A. Urquhart
    	   An Exponential Separation between Regular and General Resolution.
           Theory of Computing (2007)
    .. [2] R. Raz and P. McKenzie
           Separation of the monotone NC hierarchy.
           Combinatorica (1999)

    """
    if not is_dag(D):
        raise ValueError("Stone formulas are defined only for directed acyclic graphs.")
    
    if nstones<0:
        raise ValueError("There must be at least one stone.")

    cnf = CNF()

    if hasattr(D, 'name'):
        cnf.header = "Stone formula of: " + D.name + "\nwith " + str(nstones) + " stones\n" + cnf.header
    else:
        cnf.header = "Stone formula with " + str(nstones) + " stones\n" + cnf.header

    # add variables in the appropriate order
    vertices=enumerate_vertices(D)
    position=dict((v,i) for (i,v) in enumerate(vertices))
    stones=range(1,nstones+1)
    
    # Stones->Vertices variables
    for v in vertices:
        for j in stones:
            cnf.add_variable("P_{{{0},{1}}}".format(v,j),
                             description="Stone ${1}$ on vertex ${0}$".format(v,j))

    # Color variables
    for j in stones:
        cnf.add_variable("R_{{{0}}}".format(j),
                         description="Stone ${}$ is red".format(j))
    
    # Each vertex has some stone
    for v in vertices:
        cnf.add_clause([(True,"P_{{{0},{1}}}".format(v,j)) for j in stones])
        
    # If predecessors have red stones, the sink must have a red stone
    for v in vertices:
        for j in stones:
            pred=sorted(D.predecessors(v),key=lambda x:position[x])
            for stones_tuple in product([s for s in stones if s!=j],repeat=len(pred)):
                cnf.add_clause([(False, "P_{{{0},{1}}}".format(p,s)) for (p,s) in zip(pred,stones_tuple)] +
                               [(False, "P_{{{0},{1}}}".format(v,j))] +
                               [(False, "R_{{{0}}}".format(s)) for s in unify_list(stones_tuple)] +
                               [(True,  "R_{{{0}}}".format(j))])
        
        if D.out_degree(v)==0: #the sink
            for j in stones:
                cnf.add_clause([
                    (False,"P_{{{0},{1}}}".format(v,j)),
                    (False,"R_{{{0}}}".format(j))
                ])

    return cnf



def OrderingPrinciple(size,total=False,smart=False,plant=False,knuth=0):
    """Generates the clauses for ordering principle

    Arguments:
    - `size`  : size of the domain
    - `total` : add totality axioms (i.e. "x < y" or "x > y")
    - `smart` : "x < y" and "x > y" are represented by a single variable (implies totality)
    - `plant` : allow a single element to be minimum (could make the formula SAT)
    - `knuth` : Donald Knuth variant of the formula ver. 2 or 3 (anything else suppress it)
    """

    return GraphOrderingPrinciple(networkx.complete_graph(size),total,smart,plant,knuth)


def _graph_isomorphism_var(u, v):
    return "x_{{{0},{1}}}".format(u, v)


def GraphIsomorphism(G1, G2):
    """Graph Isomorphism formula

    The formula is the CNF encoding of the statement that two simple
    graphs G1 and G2 are isomorphic.

    Parameters
    ----------
    G1 : networkx.Graph
        an undirected graph object
    G2 : networkx.Graph
        an undirected graph object

    Returns
    -------
    A CNF formula which is satiafiable if and only if graphs G1 and G2
    are isomorphic.

    """
    F = CNF()
    F.header = "Graph Isomorphism problem between graphs " +\
               G1.name + " and " + G2.name + "\n" + F.header

    pairs = [(u, v) for u in G1.nodes() for v in G2.nodes()]
    var = _graph_isomorphism_var

    for (u, v) in pairs:
        F.add_variable(var(u, v))

    # Defined on both side
    for u in G1.nodes():
        F.add_clause([(True, var(u, v)) for v in G2.nodes()], strict=True)

    for v in G2.nodes():
        F.add_clause([(True, var(u, v)) for u in G1.nodes()], strict=True)

    # Injective on both sides
    for u in G1.nodes():
        for v1, v2 in combinations(G2.nodes(), 2):
            F.add_clause([(False, var(u, v1)),
                          (False, var(u, v2))], strict=True)
    for v in G2.nodes():
        for u1, u2 in combinations(G1.nodes(), 2):
            F.add_clause([(False, var(u1, v)),
                          (False, var(u2, v))], strict=True)

    # Edge consistency
    for u1, u2 in combinations(G1.nodes(), 2):
        for v1, v2 in combinations(G2.nodes(), 2):
            if G1.has_edge(u1, u2) != G2.has_edge(v1, v2):
                F.add_clause([(False, var(u1, v1)),
                              (False, var(u2, v2))], strict=True)
                F.add_clause([(False, var(u1, v2)),
                              (False, var(u2, v1))], strict=True)

    return F


def GraphAutomorphism(G):
    """Graph Automorphism formula

    The formula is the CNF encoding of the statement that a graph G
    has a nontrivial automorphism, i.e. an automorphism different from
    the idential one.

    Parameter
    ---------
    G : a simple graph

    Returns
    -------
    A CNF formula which is satiafiable if and only if graph G has a
    nontrivial automorphism.
    """
    tmp = CNF()
    header = "Graph automorphism formula for graph "+ G.name +"\n"+ tmp.header
    F = GraphIsomorphism(G, G)
    F.header = header

    var = _graph_isomorphism_var

    F.add_clause([(False, var(u, u)) for u in G.nodes()], strict=True)

    return F


def GraphOrderingPrinciple(graph,total=False,smart=False,plant=False,knuth=0):
    """Generates the clauses for graph ordering principle

    Arguments:
    - `graph` : undirected graph
    - `total` : add totality axioms (i.e. "x < y" or "x > y")
    - `smart` : "x < y" and "x > y" are represented by a single variable (implies `total`)
    - `plant` : allow last element to be minimum (and could make the formula SAT)
    - `knuth` : Don Knuth variants 2 or 3 of the formula (anything else suppress it)
    """
    gop = CNF()

    # Describe the formula
    if total or smart:
        name = "Total graph ordering principle"
    else:
        name = "Ordering principle"

    if smart:
        name = name + "(compact representation)"

    if hasattr(graph, 'name'):
        gop.header = name+"\n on graph "+graph.name+"\n"+gop.header
    else:
        gop.header = name+".\n"+gop.header

    #
    # Non minimality axioms
    #

    # Fix the vertex order
    V = graph.nodes()

    # Clause is generated in such a way that if totality is enforces,
    # every pair occurs with a specific orientation.
    # Allow minimum on last vertex if 'plant' options.

    for med in xrange(len(V) - (plant and 1)):
        clause = []
        for lo in xrange(med):
            if graph.has_edge(V[med], V[lo]):
                clause += [(True, 'x_{{{0},{1}}}'.format(V[lo], V[med]))]
        for hi in xrange(med+1, len(V)):
            if not graph.has_edge(V[med], V[hi]):
                continue
            elif smart:
                clause += [(False, 'x_{{{0},{1}}}'.format(V[med], V[hi]))]
            else:
                clause += [(True, 'x_{{{0},{1}}}'.format(V[hi], V[med]))]
        gop.add_clause(clause)

    #
    # Transitivity axiom
    #

    if len(V) >= 3:
        if smart:
            # Optimized version if smart representation of totality is used
            for (v1, v2, v3) in combinations(V, 3):
                gop.add_clause([(True,  'x_{{{0},{1}}}'.format(v1, v2)),
                                (True,  'x_{{{0},{1}}}'.format(v2, v3)),
                                (False, 'x_{{{0},{1}}}'.format(v1, v3))])
                gop.add_clause([(False, 'x_{{{0},{1}}}'.format(v1, v2)),
                                (False, 'x_{{{0},{1}}}'.format(v2, v3)),
                                (True,  'x_{{{0},{1}}}'.format(v1, v3))])
        elif total:
            # With totality we still need just two axiom per triangle
            for (v1, v2, v3) in combinations(V, 3):
                gop.add_clause([(False, 'x_{{{0},{1}}}'.format(v1, v2)),
                                (False, 'x_{{{0},{1}}}'.format(v2, v3)),
                                (False, 'x_{{{0},{1}}}'.format(v3, v1))])
                gop.add_clause([(False, 'x_{{{0},{1}}}'.format(v1, v3)),
                                (False, 'x_{{{0},{1}}}'.format(v3, v2)),
                                (False, 'x_{{{0},{1}}}'.format(v2, v1))])
        else:
            for (v1, v2, v3) in permutations(V, 3):

                # knuth variants will reduce the number of
                # transitivity axioms
                if knuth == 2 and ((v2 < v1) or (v2 < v3)):
                    continue
                if knuth == 3 and ((v3 < v1) or (v3 < v2)):
                    continue

                gop.add_clause([(False, 'x_{{{0},{1}}}'.format(v1, v2)),
                                (False, 'x_{{{0},{1}}}'.format(v2, v3)),
                                (True,  'x_{{{0},{1}}}'.format(v1, v3))])

    if not smart:
        # Antisymmetry axioms (useless for 'smart' representation)
        for (v1, v2) in combinations(V, 2):
            gop.add_clause([(False, 'x_{{{0},{1}}}'.format(v1, v2)),
                            (False, 'x_{{{0},{1}}}'.format(v2, v1))])

        # Totality axioms (useless for 'smart' representation)
        if total:
            for (v1, v2) in combinations(V, 2):
                gop.add_clause([(True, 'x_{{{0},{1}}}'.format(v1, v2)),
                                (True, 'x_{{{0},{1}}}'.format(v2, v1))])

    return gop


def MarkstromFormula(G):
    """Markstrom formula

    The formula is defined on a graph ``G`` and claims that it is
    possible to split the edges of the graph in two parts, so that
    each vertex has an equal number of incident edges in each part.

    The formula is defined on graphs where all vertices have even
    degree. The formula is satisfiable only on those graphs with an
    even number of vertices in each connected component [1]_.

    Arguments
    ---------
    G : networkx.Graph 
       a simple undirected graph where all vertices have even degree

    Raises
    ------
    ValueError
       if the graph in input has a vertex with odd degree

    Returns
    -------
    CNF object

    References
    ----------
    .. [1] Locality and Hard SAT-instances, Klas Markstrom
       Journal on Satisfiability, Boolean Modeling and Computation 2 (2006) 221-228

    """
    F = CNF()
    F.header = "Markstrom formula on graph " + G.name + "\n" + F.header

    def var_name(u,v):
        if u<=v:
            return 'x_{{{0},{1}}}'.format(u,v)
        else:
            return 'x_{{{0},{1}}}'.format(v,u)
    
    for (u, v) in G.edges():
        F.add_variable(var_name(u, v))

    # Defined on both side
    for v in G.nodes():

        if G.degree(v) % 2 == 1:
            raise ValueError("Markstrom formulas requires all vertices to have even degree.")

        edge_vars = [ var_name(*e) for e in G.edges(v) ]
        
        for cls in equal_to_constraint(edge_vars,
                                       len(edge_vars)/2):
            F.add_clause(cls,strict=True)

    return F


def ColoringFormula(G,colors,functional=True):
    """Generates the clauses for colorability formula

    The formula encodes the fact that the graph :math:`G` has a coloring
    with color set ``colors``. This means that it is possible to
    assign one among the elements in ``colors``to that each vertex of
    the graph such that no two adjacent vertices get the same color.

    Parameters
    ----------
    G : networkx.Graph
        a simple undirected graph
    colors : list or positive int
        a list of colors or a number of colors

    Returns
    -------
    CNF
       the CNF encoding of the coloring problem on graph ``G``

    """
    col=CNF()

    if isinstance(colors,int) and colors>=0:
        colors = range(1,colors+1)
    
    if not isinstance(list, collections.Iterable):
        ValueError("Parameter \"colors\" is expected to be a iterable")
    
    # Describe the formula
    name="colorability"
    
    if hasattr(G,'name'):
        col.header=name+" of graph:\n"+G.name+"\n"+col.header
    else:
        col.header=name+".\n"+col.header

    # Fix the vertex order
    V=G.nodes()

    # Each vertex has a color
    for vertex in V:
        clause = []
        for color in colors:
            clause += [(True,'x_{{{0},{1}}}'.format(vertex,color))]
        col.add_clause(clause)
        
        # unique color per vertex
        if functional:
            for (c1,c2) in combinations(colors,2):
                col.add_clause([
                    (False,'x_{{{0},{1}}}'.format(vertex,c1)),
                    (False,'x_{{{0},{1}}}'.format(vertex,c2))])

    # This is a legal coloring
    for (v1,v2) in G.edges():
        for c in colors:
            col.add_clause([
                (False,'x_{{{0},{1}}}'.format(v1,c)),
                (False,'x_{{{0},{1}}}'.format(v2,c))])
            
    return col


def PerfectMatchingPrinciple(graph):
    """Generates the clauses for the graph perfect matching principle.
    
    The principle claims that there is a way to select edges to such
    that all vertices have exactly one incident edge set to 1.

    Arguments:
    - `graph`  : undirected graph

    """
    cnf=CNF()

    # Describe the formula
    name="Perfect Matching Principle"
    
    if hasattr(graph,'name'):
        cnf.header=name+" of graph:\n"+graph.name+"\n"+cnf.header
    else:
        cnf.header=name+".\n"+cnf.header

    def var_name(u,v):
        if u<=v:
            return 'x_{{{0},{1}}}'.format(u,v)
        else:
            return 'x_{{{0},{1}}}'.format(v,u)
            
    # Each vertex has exactly one edge set to one.
    for v in graph.nodes():

        edge_vars = [var_name(u,v) for u in graph.adj[v]]

        # at least one edge is active
        cnf.add_clause([(True,var) for var in edge_vars])

        # at most one edge is active
        for cls in less_than_constraint(edge_vars,2):
            cnf.add_clause(cls)

    return cnf


def ParityPrinciple(size):
    """Parity rinciple on a domain with `size` elements

    Arguments:
    - `size`  : size of the domain
    """
    return GraphMatchingPrinciple(networkx.complete_graph(size))


def CountingPrinciple(M,p):
    """Generates the clauses for the counting matching principle.
    
    The principle claims that there is a way to partition M in sets of
    size p each.

    Arguments:
    - `M`  : size of the domain
    - `p`  : size of each class

    """
    cnf=CNF()

    # Describe the formula
    name="Counting Principle: {0} divided in parts of size {1}.".format(M,p)
    cnf.header=name+"\n"+cnf.header

    def var_name(tpl):
        return "Y_{{"+",".join("{0}".format(v) for v in tpl)+"}}"

    # Incidence lists
    incidence=[[] for x in range(M)]
    for tpl in combinations(range(M),p):
        for i in tpl:
            incidence[i].append(tpl)
    
    # Each element of the domain is in exactly one part.
    for el in range(M):

        edge_vars = [var_name(tpl) for tpl in incidence[el]]

        # the element is in at least one part
        cnf.add_clause([(True,var) for var in edge_vars])

        # the element is in at most one part
        for cls in strict_inequality_constraint(edge_vars,2):
            cnf.add_clause(cls)

    return cnf



def RamseyNumber(s,k,N):
    """Formula claiming that Ramsey number r(s,k) > N

    Arguments:
    - `s`: independent set size
    - `k`: clique size
    - `N`: vertices
    """

    ram=CNF()

    ram.header=dedent("""\
        CNF encoding of the claim that there is a graph of %d vertices
        with no independent set of size %d and no clique of size %d
        """ % (N,s,k)) + ram.header

    #
    # No independent set of size s
    #
    for vertex_set in combinations(xrange(1,N+1),s):
        clause=[]
        for edge in combinations(vertex_set,2):
            clause += [(True,'e_{{{0},{1}}}'.format(*edge))]
        ram.add_clause(clause)

    #
    # No clique of size k
    #
    for vertex_set in combinations(xrange(1,N+1),k):
        clause=[]
        for edge in combinations(vertex_set,2):
            clause+=[(False,'e_{{{0},{1}}}'.format(*edge))]
        ram.add_clause(clause)

    return ram


def TseitinFormula(graph,charges=None):
    """Build a Tseitin formula based on the input graph.

    Odd charge is put on the first vertex by default, unless other
    vertices are is specified in input.

    Arguments:
    - `graph`: input graph
    - `charges': odd or even charge for each vertex
    """
    V=sorted(graph.nodes())

    if charges==None:
        charges=[1]+[0]*(len(V)-1)             # odd charge on first vertex
    else:
        charges = [bool(c) for c in charges]   # map to boolean

    if len(charges)<len(V):
        charges=charges+[0]*(len(V)-len(charges))  # pad with even charges

    # init formula
    tse=CNF()
    for e in graph.edges():
        tse.add_variable("E_{{{0},{1}}}".format(*sorted(e)))

    # add constraints
    for v,c in zip(V,charges):
        
        # produce all clauses and save half of them
        names = [ "E_{{{0},{1}}}".format(*sorted(e)) for e in graph.edges_iter(v) ]
        for cls in parity_constraint(names,c):
            tse.add_clause(list(cls))

    return tse

def SubgraphFormula(graph,templates):
    """Test whether a graph contains one of the templates.

    Given a graph :math:`G` and a sequence of template graphs
    :math:`H_1`, :math:`H_2`, ..., :math:`H_t`, the CNF formula claims
    that :math:`G` contains an isomorphic copy of at least one of the
    template graphs.

    E.g. when :math:`H_1` is the complete graph of :math:`k` vertices
    and it is the only template, the formula claims that :math:`G`
    contains a :math:`k`-clique.

    Parameters
    ----------
    graph : networkx.Graph
        a simple graph
    templates : list-like object
        a sequence of graphs.

    Returns
    -------
    a CNF object
    """

    F=CNF()

    # One of the templates is chosen to be the subgraph
    if len(templates)==0:
        return F
    elif len(templates)==1:
        selectors=[]
    elif len(templates)==2:
        selectors=['c']
    else:
        selectors=['c_{{{}}}'.format(i) for i in range(len(templates))]

    if len(selectors)>1:

        # Exactly one of the graphs must be selected as subgraph
        F.add_clause([(True,v) for v in selectors])

        for (a,b) in combinations(selectors):
            F.add_clause( [ (False,a), (False,b) ] )

    # comment the formula accordingly
    if len(selectors)>1:
        F.header=dedent("""\
                 CNF encoding of the claim that a graph contains one among
                 a family of {0} possible subgraphs.
                 """.format(len(templates))) + F.header
    else:
        F.header=dedent("""\
                 CNF encoding of the claim that a graph contains an induced
                 copy of a subgraph.
                 """.format(len(templates)))  + F.header

    # A subgraph is chosen
    N=graph.order()
    k=max([s.order() for s in templates])

    for i,j in product(range(k),range(N)):
        F.add_variable("S_{{{0}}}{{{1}}}".format(i,j))

    # each vertex has an image...
    for i in range(k):
        F.add_clause([(True,"S_{{{0}}}{{{1}}}".format(i,j)) for j in range(N)])

    # ...and exactly one
    for i,(a,b) in product(range(k),combinations(range(N),2)):
        F.add_clause([(False,"S_{{{0}}}{{{1}}}".format(i,a)),
                      (False,"S_{{{0}}}{{{1}}}".format(i,b))  ])

 
    # Mapping is strictly monotone increasing (so it is also injective)
    localmaps = product(combinations(range(k),2),
                        combinations_with_replacement(range(N),2))

    for (a,b),(i,j) in localmaps:
        F.add_clause([(False,"S_{{{0}}}{{{1}}}".format(min(a,b),max(i,j))),
                      (False,"S_{{{0}}}{{{1}}}".format(max(a,b),min(i,j)))  ])


    # The selectors choose a template subgraph.  A mapping must map
    # edges to edges and non-edges to non-edges for the active
    # template.

    if len(templates)==1:

        activation_prefixes = [[]]

    elif len(templates)==2:

        activation_prefixes = [[(True,selectors[0])],[(False,selectors[0])]]

    else:
        activation_prefixes = [[(True,v)] for v in selectors]


    # maps must preserve the structure of the template graph
    gV = graph.nodes()

    for i in range(len(templates)):


        k  = templates[i].order()
        tV = templates[i].nodes()

        localmaps = product(combinations(range(k),2),
                            combinations(range(N),2))


        for (i1,i2),(j1,j2) in localmaps:

            # check if this mapping is compatible
            tedge=templates[i].has_edge(tV[i1],tV[i2])
            gedge=graph.has_edge(gV[j1],gV[j2])
            if tedge == gedge: continue

            # if it is not, add the corresponding
            F.add_clause(activation_prefixes[i] + \
                         [(False,"S_{{{0}}}{{{1}}}".format(min(i1,i2),min(j1,j2))),
                          (False,"S_{{{0}}}{{{1}}}".format(max(i1,i2),max(j1,j2))) ])

    return F


def RandomKCNF(k, n, m, seed=None):
    """Build a random k-CNF

    Sample :math:`m` clauses over :math:`n` variables, each of width
    :math:`k`, uniformly at random. The sampling is done without
    repetition, meaning that whenever a randomly picked clause is
    already in the CNF, it is sampled again.

    If the sampling takes too long (i.e. the space of possible clauses
    is too small) then a ``RuntimeError`` is raised.

    Parameters
    ----------
    k : int
       width of each clause
    
    n : int
       number of variables to choose from. The resulting CNF object 
       will contain n variables even if some are not mentioned in the clauses.
    
    m : int
       number of clauses to generate
    
    seed : hashable object
       seed of the random generator

    Returns
    -------
    a CNF object

    Raises
    ------
    ValueError 
        when some paramenter is negative, or when k>n.
    RuntimeError
        the formula is too dense for the simple sampling process.

    """
    import random
    if seed: random.seed(seed)


    if k>n or n<0 or m<0 or k<0:
        raise ValueError("Parameters must be non-negatives.")
        
    F = CNF()
    F.header = "Random {}-CNF over {} variables and {} clauses\n".format(k,n,m) + F.header
    
    for variable in xrange(1,n+1):
        F.add_variable(variable)

    clauses = set()
    t = 0
    while len(clauses)<m and t < 10*m:
        t += 1
        clauses.add(tuple((random.choice([True,False]),x+1)
                      for x in sorted(random.sample(xrange(n),k))))
    if len(clauses)<m:
        raise RuntimeError("Sampling is taking too long. Maybe the requested formula is too dense.")
    for clause in clauses:
        F.add_clause(list(clause))

    return F
 
