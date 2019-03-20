import fnmatch # Quick hack to enable wildcards

ASSIGN = "="
RENAME = "rho"
RENAME_ALL = "RHO"
RENAME_TABLE = "tau"
EXTRA_COLUMN = "gamma"
PROJECTION = "pi"
CONDITION = "sigma"
EQUALS = "=="
INPUT1 = "times1"
INPUT2 = "times2"
CONSTANT = "constant"

SELECT = "select"
OR = "or"
AND = "and"
NOT = "not"
EQUALS = "=="
NOT_EQUAL = "!="
SMALLER = "<"
BIGGER = ">"
SMALLER_EQUAL = "<="
BIGGER_EQUAL  = ">="

INPUTS = { INPUT1, INPUT2 }
COMPARE = { EQUALS, NOT_EQUAL, SMALLER, BIGGER, SMALLER_EQUAL, BIGGER_EQUAL }
LOGICAL = { AND, OR, NOT }
BOOLEAN = COMPARE | LOGICAL
BOOL_EXPR = BOOLEAN | { CONSTANT }

canonical_select_stmt = {
    ASSIGN: (CONSTANT, { RENAME, EXTRA_COLUMN, PROJECTION, CONDITION} ),
    RENAME: (CONSTANT, { RENAME, EXTRA_COLUMN, PROJECTION, CONDITION} ),
    EXTRA_COLUMN: (CONSTANT, { EXTRA_COLUMN, PROJECTION, CONDITION} ),
    PROJECTION: (CONSTANT, { CONDITION} ),
    CONDITION: (BOOL_EXPR, { x for x in INPUTS }),
    INPUT1: ( { CONSTANT } ),
    INPUT2: ( RENAME_ALL, RENAME_ALL ),
    RENAME_ALL: ( CONSTANT, CONSTANT ),
    CONSTANT: ( set() )
}
for boolean in BOOLEAN:
    canonical_select_stmt[boolean] = (BOOL_EXPR, BOOL_EXPR)

class TreeNode:
    def __init__(self, node_type, children):
        self.node_type = node_type
        self.children = children
        self.parent = None
        self.parent_index = -1
        for n, child in enumerate(children):
            if child:
                child.set_parent(self, n)

    def show(self):
        print(self.node_type)
        print("{")
        for child in self.children:
            if child:
                child.show()
            else:
                print("None")
            print(",")
        print("}")
    def get_nodetype(self):
        return self.node_type
    def get_children(self):
        return self.children
    def get_parent(self):
        return (self.parent, self.parent_index)
    def remove_child(self, n):
        removed_child = self.children[n]
        self.children[n] = None
        return removed_child
    def clone(self):
        return TreeNode(self.node_type, [ child.clone() for child in self.children ])
    def set_parent(self, parent, index):
        self.parent = parent
        self.parent_index = index
    def set_child(self, n, child):
        self.children[n] = child
        child.set_parent(self, n)

class ConstNode(TreeNode):
    def __init__(self, value):
        TreeNode.__init__(self, CONSTANT, [])
        self.value = value
    def show(self):
        print(self.node_type)
        print(self.value)
    def get_value(self):
        return self.value
    def clone(self):
        return ConstNode(self.value)

def test_treenode_init():
    X_expr = ConstNode("X")
    RHOX_expr = TreeNode(RENAME_ALL, [X_expr, X_expr])
    Y_expr = ConstNode("Y")
    RHOY_expr = TreeNode(RENAME_ALL, [Y_expr, Y_expr])
    join_expr = TreeNode(INPUT2, [RHOX_expr, RHOY_expr])
    a_expr = ConstNode("a")
    two_expr = ConstNode("2")
    is_expr = TreeNode(EQUALS, [a_expr, two_expr])
    b_expr = ConstNode("b")
    three_expr = ConstNode("3")
    not_is_expr = TreeNode(NOT_EQUAL, [b_expr, three_expr])
    and_expr = TreeNode(AND, [is_expr, not_is_expr])
    sigma_expr = TreeNode(CONDITION, [and_expr, join_expr])
    var_expr = ConstNode(["a", "b", "c"])
    pi_expr = TreeNode(PROJECTION, [var_expr, sigma_expr])
    col_expr = ConstNode(["x", '"one"'])
    gamma_expr = TreeNode(EXTRA_COLUMN, [col_expr, pi_expr])
    ren_expr = ConstNode(["y", "a"])
    rho_expr = TreeNode(RENAME, [ren_expr, gamma_expr])
    ren2_expr = ConstNode(["z", "x"])
    rho2_expr = TreeNode(RENAME, [ren2_expr, rho_expr])
    B_expr = ConstNode("B")
    equals_expr = TreeNode(ASSIGN, [B_expr, rho2_expr])

    equals_expr.show()
    return equals_expr

def find_deviation_node(expr, expr_format, expected_types):
    """Finds the first node in expr that has a type that is not expected based on expr_format.
       When calling find_deviation_node, expected_types must be assigned the expected type
       for the root node."""

    if expr.get_nodetype() not in expected_types:
        return expr
    children = expr.get_children()
    node_format = expr_format[expr.get_nodetype()]
    for n, child in enumerate(children):
        result = find_deviation_node(child, expr_format, node_format[n])
        if result is not None:
            return result 
    return None

def validate_expression_format(expr, expr_format, expected_types):

    return find_deviation_node(expr, expr_format, expected_types) is None

def test_validate_expression_format():
    expr = test_treenode_init()
    dev = find_deviation_node(expr, canonical_select_stmt, {ASSIGN})
    if dev is None:
        print(dev)
    else:
        dev.show()
    print(validate_expression_format(expr, canonical_select_stmt, {ASSIGN}))

def test_canonical_select(expr):
    if expr.get_nodetype() != ASSIGN:
        return False
    subexpr = expr.get_children()[1]
    while subexpr.get_nodetype() == RENAME:
        subexpr = subexpr.get_children()[1]
    while subexpr.get_nodetype() == EXTRA_COLUMN:
        subexpr = subexpr.get_children()[1]
    if subexpr.get_nodetype() == PROJECTION:
        subexpr = subexpr.get_children()[1]
    if subexpr.get_nodetype() == CONDITION:
        subexpr = subexpr.get_children()[1]
    if subexpr.get_nodetype() not in INPUTS:
        return False
    return True

def make_select_expr(expr):
    into_expr = expr.get_children()[0]
    subexpr = expr.get_children()[1]
    if subexpr.get_nodetype() in [ RENAME, EXTRA_COLUMN, PROJECTION ]:
        columns_expr = subexpr
        while True:
            new_subexpr = subexpr.get_children()[1]
            if new_subexpr.get_nodetype() not in [ RENAME, EXTRA_COLUMN, PROJECTION ]:
                subexpr.remove_child(1)
                subexpr = new_subexpr
                break
            subexpr = new_subexpr
    else:
        columns_expr = None
    if subexpr.get_nodetype() == CONDITION:
        where_expr = subexpr
        subexpr = where_expr.remove_child(1)
    else:
        where_expr = None
    from_expr = subexpr

    select_expr = TreeNode(SELECT, [columns_expr, into_expr, from_expr, where_expr])
    return select_expr

def get_skip_nodes(expr, nodetype):
    if expr.get_nodetype() != nodetype:
        return ([], expr)

    typenodes = []
    while expr:
        typenodes.append(expr.get_children()[0].get_value())
        expr = expr.get_children()[1]
        if expr.get_nodetype() != nodetype:
            break
    nextnode = expr
    return (typenodes, nextnode)

def gen_columns_stmt(expr):
    if not expr:
        return "*"

    (rename_columns, expr) = get_skip_nodes(expr, RENAME)        
    (extra_columns, expr) = get_skip_nodes(expr, EXTRA_COLUMN)
    if expr and expr.get_nodetype() == PROJECTION:
        projection_expr = expr
    else:
        projection_expr = None

    if not projection_expr:
        return "*"
    columns = {}

    columns = [ [ colname, None ] for colname in projection_expr.get_children()[0].get_value() ] 
    for extra_column in extra_columns:
        columns.append([extra_column[1], extra_column[0]])
    for rename_column in rename_columns:
        for column in columns:
            colname = column[1] or column[0]
            if colname == rename_column[1]:
                column[1] = rename_column[0]
                break

    stmt = ""
    for column in columns:
        if stmt:
            stmt += ", "
        stmt += column[0]
        if column[1]:
            stmt += " AS " + column[1]
    
    return stmt

def gen_into_stmt(expr):

    return "INTO " + expr.get_value()

def gen_from_stmt(expr):

    stmt = ""
    names_expr = expr.get_children()
    for name_expr in names_expr:
        if name_expr.get_nodetype() == CONSTANT:
            name = name_expr.get_value()
        else:
            name = name_expr.get_children()[1].get_value()
        if stmt:
            stmt += " JOIN "
        stmt += name

    return "FROM " + stmt

def gen_conditional(expr):
    
    if expr.get_nodetype() == CONSTANT:
        return "(" + expr.get_value() + ")"
    if expr.get_nodetype() == NOT:
        return "(NOT " + gen_conditional(expr.get_children()[0]) + ")"
    if expr.get_nodetype() == OR:
        operator = " OR "
    elif expr.get_nodetype() == AND:
        operator = " AND "
    elif expr.get_nodetype() == EQUALS:
        operator = " = "
    elif expr.get_nodetype() == NOT_EQUAL:
        operator = " <> "
    elif expr.get_nodetype() == SMALLER:
        operator = " < "
    elif expr.get_nodetype() == BIGGER:
        operator = " > "
    elif expr.get_nodetype() == SMALLER_EQUAL:
        operator = " <= "
    elif expr.get_nodetype() == BIGGER_EQUAL:
        operator = " >= "
    
    return "(" + gen_conditional(expr.get_children()[0]) + operator + gen_conditional(expr.get_children()[1]) + ")"
    
def gen_where_stmt(expr):
    if not expr:
        return ""
    return "WHERE " + gen_conditional(expr.get_children()[0])

def gen_select_stmt(expr):

    children = expr.get_children()
    stmt = "SELECT " + gen_columns_stmt(children[0]) + " " + gen_into_stmt(children[1]) + " " + gen_from_stmt(children[2]) + " " + gen_where_stmt(children[3])
    return stmt

def print_as_SQL(expr):
    clone_expr = expr.clone()
    select_expr = make_select_expr(clone_expr)
    print(gen_select_stmt(select_expr))

def elementary_test():
    # Build up select statement
    X_expr = ConstNode("X")
    Y_expr = ConstNode("Y")
    join_expr = TreeNode(INPUT2, [X_expr, Y_expr])
    a_expr = ConstNode("a")
    two_expr = ConstNode("2")
    is_expr = TreeNode(EQUALS, [a_expr, two_expr])
    b_expr = ConstNode("b")
    three_expr = ConstNode("3")
    not_is_expr = TreeNode(NOT_EQUAL, [b_expr, three_expr])
    and_expr = TreeNode(AND, [is_expr, not_is_expr])
    sigma_expr = TreeNode(CONDITION, [and_expr, join_expr])
    var_expr = ConstNode(["a", "b", "c"])
    pi_expr = TreeNode(PROJECTION, [var_expr, sigma_expr])
    col_expr = ConstNode(["x", '"one"'])
    gamma_expr = TreeNode(EXTRA_COLUMN, [col_expr, pi_expr])
    ren_expr = ConstNode(["y", "a"])
    rho_expr = TreeNode(RENAME, [ren_expr, gamma_expr])
    ren2_expr = ConstNode(["z", "x"])
    rho2_expr = TreeNode(RENAME, [ren2_expr, rho_expr])
    B_expr = ConstNode("B")
    equals_expr = TreeNode(ASSIGN, [B_expr, rho2_expr])

    # Clone select statement
    clone_expr = equals_expr.clone()
    clone_expr.get_children()[0].value = "C"

    print(test_canonical_select(equals_expr)) # Should be 'True'

    # Generate SQL code
    select_expr = make_select_expr(equals_expr)
    select2_expr = make_select_expr(clone_expr)
    print(gen_select_stmt(select_expr)) # Should be 'SELECT a AS y, b, c, "one" AS z INTO B FROM X JOIN Y WHERE (((a) = (2)) AND ((b) <> (3)))'
    print(gen_select_stmt(select2_expr)) # Should be 'SELECT a AS y, b, c, "one" AS z INTO C FROM X JOIN Y WHERE (((a) = (2)) AND ((b) <> (3)))'


def find_node(expr, node_types):
    if not isinstance(node_types, set):
        node_types = [ node_types ]

    if expr.get_nodetype() in node_types:
        return expr

    for child in expr.get_children(): 
        found = find_node(child, node_types)
        if found:
            return found
    return None

def substitute(source, target):
    """ Substitutes any reference of source in target by source """

    source_name = source.get_children()[0].get_value()
    input_node = find_node(target, INPUTS)
    for n, child in enumerate(input_node.get_children()):
        name = child.get_children()[1].get_value()
        if name == source_name:
            child.set_child(1, source.get_children()[1])
            break

def replace_columns_conditional(expr, src_column, tgt_column):

    if expr.get_nodetype() == CONSTANT:
        if expr.value == src_column:
            expr.value = tgt_column
    else:
        for child in expr.get_children():
            replace_columns_conditional(child, src_column, tgt_column)

def intersection_with_wildcards(l, m):

    result = set()
    for elt1 in l:
        for elt2 in m:
            if fnmatch.fnmatch(elt1, elt2) or fnmatch.fnmatch(elt2, elt1):
                if "*" not in elt1:
                    result.add(elt1)
                elif "*" not in elt2:
                    result.add(elt2)
    return result

def lift_cleanup_node(cleanup_node, expr_format):

    this_type = cleanup_node.get_nodetype()
    prev_node = cleanup_node
    (parent, index) = cleanup_node.get_parent()
    node_format = expr_format[parent.get_nodetype()]
    if cleanup_node.get_nodetype() not in node_format[index]:
        parent.set_child(index, cleanup_node.get_children()[1])

    delete_node = False
    while not delete_node and cleanup_node.get_nodetype() not in node_format[index]:
        if this_type == RENAME:
            if parent.get_nodetype() == RENAME_ALL:
                cleanup_node.children[0].value = [ parent.get_children()[0].value + "." + x for x in cleanup_node.children[0].value ]
            elif parent.get_nodetype() == CONDITION:
                replace_columns_conditional(parent.get_children()[0], cleanup_node.children[0].value[0], cleanup_node.children[0].value[1])
            elif parent.get_nodetype() == PROJECTION:
                for n, value in enumerate(parent.get_children()[0].value):
                    if value == cleanup_node.children[0].value[0]:
                        parent.get_children()[0].value[n] = cleanup_node.children[0].value[1]
                        break
        elif this_type == PROJECTION:
            if parent.get_nodetype() == RENAME_ALL:
                cleanup_node.children[0].value = [ parent.get_children()[0].value + "." + x for x in cleanup_node.children[0].value ]
            elif parent.get_nodetype() in INPUTS:
                for child in parent.get_children():
                    if child == prev_node:
                        continue
                    cleanup_node.children[0].value.append(child.get_children()[0].value + ".*")
            elif parent.get_nodetype() == PROJECTION:
                this_args = cleanup_node.get_children()[0].value
                parent_args = parent.get_children()[0].value
                #parent.get_children()[0].value = [ x for x in { y for y in this_args} | { z for z in parent_args } ]
                parent.get_children()[0].value = intersection_with_wildcards(this_args, parent_args)
                delete_node = True
        prev_node = parent
        (parent, index) = parent.get_parent()
        node_format = expr_format[parent.get_nodetype()]
    if not delete_node:
        cleanup_node.set_child(1, parent.get_children()[index])
        parent.set_child(index, cleanup_node)

def cleanup_expr(expr, expr_format):

    cleanup_node = find_deviation_node(expr, expr_format, { ASSIGN } )

    while cleanup_node:
        lift_cleanup_node(cleanup_node, expr_format)
        cleanup_node = find_deviation_node(expr, expr_format, { ASSIGN } )
    return expr

def substitute_test():
    tbl_expr = ConstNode("tbl_persoon")
    from_expr = TreeNode(INPUT1, [tbl_expr])
    col_expr = ConstNode(["id", "adres"])
    pi_expr = TreeNode(PROJECTION, [col_expr, from_expr])
    ren_expr = ConstNode(["x", "adres"])
    rho_expr = TreeNode(RENAME, [ren_expr, pi_expr])
    A_expr = ConstNode("A")
    A_equals_expr = TreeNode(ASSIGN, [A_expr, rho_expr])

    tbl_expr = ConstNode("tbl_adres")
    from_expr = TreeNode(INPUT1, [tbl_expr])
    col_expr = ConstNode(["id", "gemeente"])
    pi_expr = TreeNode(PROJECTION, [col_expr, from_expr])
    ren_expr = ConstNode(["x", "gemeente"])
    rho_expr = TreeNode(RENAME, [ren_expr, pi_expr])
    B_expr = ConstNode("B")
    B_equals_expr = TreeNode(ASSIGN, [B_expr, rho_expr])

    A2_expr = ConstNode("A")
    B2_expr = ConstNode("B")
    join_expr = TreeNode(INPUT2, [
        TreeNode(RENAME_ALL, [
            ConstNode("A"),
            ConstNode("A")
        ]),
        TreeNode(RENAME_ALL, [
            ConstNode("B"),
            ConstNode("B")            
        ])
    ])
    Ax_expr = ConstNode("A.x")
    Bid_expr = ConstNode("B.id")
    cond_expr = TreeNode(EQUALS, [Ax_expr, Bid_expr])
    sigma_expr = TreeNode(CONDITION, [cond_expr, join_expr])
    col_expr = ConstNode(["A.id", "B.x"])
    pi_expr = TreeNode(PROJECTION, [col_expr, sigma_expr])
    ren_expr = ConstNode(["id", "A.id"])
    rho_expr = TreeNode(RENAME, [ren_expr, pi_expr])
    ren_expr = ConstNode(["x", "B.x"])
    rho_expr = TreeNode(RENAME, [ren_expr, rho_expr])
    C_expr = ConstNode("C")
    C_equals_expr = TreeNode(ASSIGN, [C_expr, rho_expr])

    print(test_canonical_select(A_equals_expr))
    print(test_canonical_select(B_equals_expr))
    print(test_canonical_select(C_equals_expr))
    print_as_SQL(A_equals_expr)
    print_as_SQL(B_equals_expr)
    print_as_SQL(C_equals_expr)

    A2_expr = A_equals_expr.clone()
    B2_expr = B_equals_expr.clone()
    C2_expr = C_equals_expr.clone()

    A2_expr.show()
    C2_expr.show()
    substitute(A2_expr, C2_expr)
    cleanup_expr(C2_expr, canonical_select_stmt)
    C2_expr.show()

if __name__ == "__main__":
    substitute_test()