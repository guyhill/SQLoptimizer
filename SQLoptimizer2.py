from enum import Flag, unique, auto

@unique
class NodeType(Flag):
    ASSIGN = auto()
    RENAME = auto()
    RENAME_TABLE = auto()
    EXTRA_COLUMN = auto()
    PROJECTION = auto()
    CONDITION = auto()
    INPUT1 = auto()
    INPUT2 = auto()
    CONSTANT = auto()
    TABLE = auto()
    TABLENAME = auto()
    COLUMNNAME = auto()
    COLSPEC = auto()
    COLSPECLIST = auto()
    OR = auto()
    AND = auto()
    NOT = auto()
    EQUALS = auto()
    NOT_EQUAL = auto()
    SMALLER = auto()
    BIGGER = auto()
    SMALLER_EQUAL = auto()
    BIGGER_EQUAL  = auto()

    INPUTS = INPUT1 | INPUT2
    COMPARE = EQUALS | NOT_EQUAL | SMALLER | BIGGER | SMALLER_EQUAL | BIGGER_EQUAL
    LOGICAL = AND | OR | NOT
    BOOLEAN = COMPARE | LOGICAL
    BOOL_EXPR = BOOLEAN | CONSTANT

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
    def get_child(self, n):
        if n >= len(self.children):
            return None
        else:
            return self.children[n]
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
    def find_node(self, node_type, isCheckSelf = True):
        if isCheckSelf and self.node_type == node_type:
            return self
        for child in self.children:
            result = child.find_node(node_type)
            if result is not None:
                return result
        return None

class ConstNode(TreeNode):
    def __init__(self, value):
        TreeNode.__init__(self, NodeType.CONSTANT, [])
        self.value = value
    def show(self):
        print(self.node_type)
        print(self.value)
    def get_value(self):
        return self.value
    def clone(self):
        return ConstNode(self.value)

def get_colspec_name(colspec_node):
    table_name = colspec_node.get_child(0).get_value()
    column_name = colspec_node.get_child(1).get_value()
    return table_name + "." + column_name

def gen_select_stmt(expr):
    """Generate a SELECT statement from an expr. We assume that expr is in select canonical form
    
       TODO: WHERE clause
    """
    assign_node = expr.find_node(NodeType.ASSIGN)
    result_name = assign_node.get_child(1).get_value()
    into_clause = " INTO " + result_name

    table_node = expr.find_node(NodeType.TABLE)
    table_name = table_node.get_child(0).get_value()
    table_alias = table_node.get_child(1).get_value()
    from_clause = " FROM " + table_name + " AS " + table_alias

    columns = []
    projection_node = expr.find_node(NodeType.PROJECTION)
    for colspec_node in projection_node.find_node(NodeType.COLSPECLIST).get_children():
        columns.append([get_colspec_name(colspec_node), None])

    rename_expr = expr.find_node(NodeType.RENAME)
    while rename_expr:
        src_name = get_colspec_name(rename_expr.get_child(2))
        tgt_name = rename_expr.get_child(1).get_value()
        for column in columns:
            if column[0] == src_name:
                column[1] = tgt_name
                break
        rename_expr = rename_expr.find_node(NodeType.RENAME, False)

    columns_clause = ""
    for column in columns:
        if columns_clause:
            columns_clause += ", "
        columns_clause += column[0]
        if column[1] is not None:
            columns_clause += " AS " + column[1]

    #return "FROM " + table_name + " AS " + table_alias
    return "SELECT " + columns_clause + into_clause + from_clause

def make_select_expr(columns, columns_alias, result_name, table_name, table_alias):

    table_expr = TreeNode(NodeType.TABLE, [ConstNode(table_name), ConstNode(table_alias)])
    colspecs_list = [ TreeNode(NodeType.COLSPEC, [ConstNode(table_alias), ConstNode(column)]) for column in columns ]
    colspeclist_expr = TreeNode(NodeType.COLSPECLIST, colspecs_list)
    projection_expr = TreeNode(NodeType.PROJECTION, [table_expr, colspeclist_expr])
    rename_expr = projection_expr
    for (column, alias) in zip(columns, columns_alias):
        if alias is not None:
            colspec_expr = TreeNode(NodeType.COLSPEC, [ConstNode(table_alias), ConstNode(column)])
            rename_expr = TreeNode(NodeType.RENAME, [rename_expr, ConstNode(alias), colspec_expr])
    assign_expr = TreeNode(NodeType.ASSIGN, [rename_expr, ConstNode(result_name)])    
    return assign_expr

if __name__ == "__main__":
    expr = make_select_expr(["id", "adres"], [None, "x"], "X", "tblPersoon", "A")
    print(gen_select_stmt(expr))
