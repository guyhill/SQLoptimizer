from enum import Flag, unique, auto
from collections import namedtuple

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
    TEMP_TABLE = auto()
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


class TreeNode():
    def __init__(self, children = None):
        if not children:
            children = []
        if not isinstance(children, list):
            children = [ children ]
        self.children = children

    def get_child(self, n):
        if n >= len(self.children):
            return None
        return self.children[n]

    def get_children(self):
        return self.children

    def DepthFirst(self):
        yield self
        for child in self.children:
            yield from child.DepthFirst()
    
    def DepthFirstReversed(self):
        for child in self.children:
            yield from child.DepthFirst()
        yield self

    def add_child(self, child):
        self.children.append(child)

class ParseTreeNode(TreeNode):
    def __init__(self, data, children = []):
        self.data = data
        super().__init__(children)

    def find_node(self, data, isCheckSelf = True):
        for node in self.DepthFirst():
            if node.data == data and (isCheckSelf or node != self):
                return node
        return None

    def get_value(self):
        return self.data


class InterParseTree():
    def __init__(self, expression):
        self.expression = expression
        self.root = self.parse()

    def parse(self):
        self.parse_pos = 0
        (ok, tree) = self.parse_expr()
        if ok:
            return tree
        else:
            raise SyntaxError

    def parse_operator_expr(self):
        cur_pos = self.parse_pos
        (ok, operator) = self.parse_operator()
        if not ok:
            self.parse_pos = cur_pos
            return (False, None)
        if self.expression[self.parse_pos] != "(":
            self.parse_pos = cur_pos
            return (False, None)
        self.parse_pos += 1
        (ok, args) = self.parse_args()
        if not ok:
            self.parse_pos = cur_pos
            return (False, None)
        if self.expression[self.parse_pos] != ")":
            self.parse_pos = cur_pos
            return (False, None)
        self.parse_pos += 1
        return (True, ParseTreeNode(operator, args))

    def parse_operator(self):
        operator = self.expression[self.parse_pos]
        if operator not in "aiko":
            return (False, None)
        self.parse_pos += 1
        return (True, operator)

    def parse_args(self):
        cur_pos = self.parse_pos
        (ok, arg) = self.parse_expr()
        if not ok:
            return (False, None)
        if self.expression[self.parse_pos] == ",":
            self.parse_pos += 1
            (ok, args) = self.parse_args()
            if ok:
                return (True, [arg] + args)
            else:
                self.parse_pos = cur_pos
                return (False, None)
        else:
            return (True, [arg])

    def parse_expr(self):
        (ok, op_expr) = self.parse_operator_expr()
        if ok:
            return (True, op_expr)
        cur_pos = self.parse_pos
        arrow_name = ""
        while self.parse_pos < len(self.expression) and \
              self.expression[self.parse_pos] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_":
            arrow_name += self.expression[self.parse_pos]
            self.parse_pos += 1
        if len(arrow_name) < 2:
            self.parse_pos = cur_pos
            return (False, None)
        return (True, ParseTreeNode(arrow_name, []))
    
    def generate_ralg_expr(self):

        db_designs = {
            "woont_op": ("tbl_persoon", "persoons_id", "adres_id"),
            "ligt_in": ("tbl_ades", "adres_id", "gemeente_id"),
            "onderdeel_van": ("tbl_gemeente", "gemeente_id", "provincie_id")
        }
        tablenames = {}
        n_tables = 0
        for node in self.root.DepthFirstReversed():
            if len(node.data) == 1:    # operator
                if node.data == "o":   # composition
                    src_tablenames = [ tablenames[id(child)] for child in node.children ] 
                    tgt_tablename = f"T{n_tables}"
                    n_tables += 1
                    tablenames[id(node)] = tgt_tablename
                    ralg_expr = make_comp_expr(tgt_tablename, src_tablenames)
            else:
                src_tablename = f"T{n_tables}"
                tgt_tablename = f"T{n_tables + 1}"
                n_tables += 2
                tablenames[id(node)] = tgt_tablename
                db_design = db_designs[node.data]
                ralg_expr = make_select_expr(db_design[1:3], ("domain", "codomain"), tgt_tablename, db_design[0], src_tablename)
            
            print(gen_select_stmt(ralg_expr))


ColSpec = namedtuple("ColSpec", ["table", "column"])


class RenameNode(TreeNode):

    def __init__(self, table = None):
        super().__init__(table)
        self.arguments = {}

    def add_columns(self, table, columns, aliases):
        for column, alias in zip(columns, aliases):
            self.arguments[ColSpec(table, column)] = alias

    def combine(self, other):
        for colspec, alias in other.arguments.items():
            renamed_colspec = ColSpec(colspec.table, alias)
            if renamed_colspec in self.arguments:
                current_alias = self.arguments[renamed_colspec]
                del self.arguments[renamed_colspec]
                self.arguments[colspec] = current_alias
            else:
                self.arguments[colspec] = alias
        return self

    def __str__(self):
        result = ""
        if len(self.children) == 1 and isinstance(self.children[0], ProjectionNode):
            columns = list(self.children[0].columns)
            for colspec in columns:
                if result != "":
                    result += ", "
                result += f"{colspec.table}.{colspec.column}"
                if colspec in self.arguments:
                    result += f" AS {self.arguments[colspec]}"
        else:
            for colspec, alias in self.arguments.items():
                if result != "":
                    result += ", "
                result += f"{colspec.table}.{colspec.column} AS {self.arguments[colspec]}"
        return result


class ProjectionNode(TreeNode):

    def __init__(self, table = None):
        super().__init__(table)
        self.columns = set()
    
    def add_columns(self, table, columns):
        for column in columns:
            self.columns.add(ColSpec(table, column))

    def combine(self, other):
        if isinstance(other, ProjectionNode):
            self.columns &= other.columns
        elif isinstance(other, RenameNode):
            for colspec, alias in other.arguments.items():
                renamed_colspec = ColSpec(colspec.table, alias)
                if renamed_colspec in self.columns:
                    self.columns.remove(renamed_colspec)
                    self.columns.add(colspec)

    def __str__(self):
        result = ""
        for colspec in self.columns:
            if result != "":
                result += ", "
            result += f"{colspec.table}.{colspec.column}"
        return result


class TableNode(TreeNode):

    def __init__(self, tablename, tablealias):
        super().__init__()
        self.tablename = tablename
        self.tablealias = tablealias

    def __str__(self):
        return f"{self.tablename} AS {self.tablealias}"


class AssignNode(TreeNode):

    def __init__(self, table, name):
        super().__init__(table)
        self.name = name

    def set_name(self, name):
        self.name = name

    def __str__(self):
        return self.name


class JoinNode(TreeNode):

    def __init__(self, tables):
        super().__init__(tables)


class ConditionalNode(TreeNode):

    def __init__(self, )
def gen_conditional(expr):
    
    if expr.data == NodeType.CONSTANT:
        return "(" + expr.get_value() + ")"
    elif expr.data == NodeType.COLSPEC:
        return "(" + expr.get_child(0).get_value() + "." + expr.get_child(1).get_value() + ")"
    elif expr.data == NodeType.NOT:
        return "(NOT " + gen_conditional(expr.get_children()[0]) + ")"
    elif expr.data == NodeType.OR:
        operator = " OR "
    elif expr.data == NodeType.AND:
        operator = " AND "
    elif expr.data == NodeType.EQUALS:
        operator = " = "
    elif expr.data == NodeType.NOT_EQUAL:
        operator = " <> "
    elif expr.data == NodeType.SMALLER:
        operator = " < "
    elif expr.data == NodeType.BIGGER:
        operator = " > "
    elif expr.data == NodeType.SMALLER_EQUAL:
        operator = " <= "
    elif expr.data == NodeType.BIGGER_EQUAL:
        operator = " >= "
    
    return "(" + gen_conditional(expr.get_children()[0]) + operator + gen_conditional(expr.get_children()[1]) + ")"

def get_colspec_name(colspec_node):
    table_name = colspec_node.get_child(0).get_value()
    column_name = colspec_node.get_child(1).get_value()
    return table_name + "." + column_name

# def gen_select_stmt(expr):
#     """Generate a SELECT statement from an expr. We assume that expr is in select canonical form
    
#        TODO: WHERE clause
#     """
#     assign_node = expr.find_node(NodeType.ASSIGN)
#     result_name = assign_node.get_child(1).get_value()
#     into_clause = " INTO " + result_name

#     table_node = expr.find_node(NodeType.TABLE)
#     if table_node is not None:
#         table_name = table_node.get_child(0).get_value()
#         table_alias = table_node.get_child(1).get_value()
#         from_clause = " FROM " + table_name + " AS " + table_alias
#     else:
#         inputs_node = expr.find_node(NodeType.INPUT2)
#         input1_node = inputs_node.get_child(0)
#         table1_alias = input1_node.get_child(1).get_value()
#         table1_tempname = input1_node.find_node(NodeType.TEMP_TABLE).get_child(0).get_value()
#         input2_node = inputs_node.get_child(1)
#         table2_alias = input2_node.get_child(1).get_value()
#         table2_tempname = input2_node.find_node(NodeType.TEMP_TABLE).get_child(0).get_value()
#         from_clause = f" FROM {table1_tempname} AS {table1_alias} JOIN {table2_tempname} AS {table2_alias} "

#     columns = []
#     projection_node = expr.find_node(NodeType.PROJECTION)
#     for colspec_node in projection_node.find_node(NodeType.COLSPECLIST).get_children():
#         columns.append([get_colspec_name(colspec_node), None])

#     rename_expr = expr.find_node(NodeType.RENAME)
#     while rename_expr:
#         src_name = get_colspec_name(rename_expr.get_child(2))
#         tgt_name = rename_expr.get_child(1).get_value()
#         for column in columns:
#             if column[0] == src_name:
#                 column[1] = tgt_name
#                 break
#         rename_expr = rename_expr.find_node(NodeType.RENAME, False)

#     columns_clause = ""
#     for column in columns:
#         if columns_clause:
#             columns_clause += ", "
#         columns_clause += column[0]
#         if column[1] is not None:
#             columns_clause += " AS " + column[1]

#     cond_expr = expr.find_node(NodeType.CONDITION)
#     if cond_expr:
#         where_clause = "WHERE " + gen_conditional(cond_expr.get_child(1))
#     else:
#         where_clause = ""

#     return "SELECT " + columns_clause + into_clause + from_clause + where_clause


def gen_select_stmt(expr):

    if isinstance(expr, AssignNode):
        into_stmt = " INTO " + str(expr)
        expr = expr.get_child(0)
    else:
        into_stmt = ""
    if isinstance(expr, RenameNode):
        columns_stmt = str(expr)
        expr = expr.get_child(0).get_child(0)
    elif isinstance(expr, ProjectionNode):
        columns_stmt = str(expr)
        expr = expr.get_child(0)
    if isinstance(expr, TableNode):
        from_stmt = " FROM " + str(expr)
    if columns_stmt == "" and from_stmt == "":
        raise SyntaxError
    
    return "SELECT " + columns_stmt + into_stmt + from_stmt
    

def make_comp_expr(output_table, input_tables):

    table1_expr = ParseTreeNode(NodeType.TEMP_TABLE, [ParseTreeNode(input_tables[0])])
    table2_expr = ParseTreeNode(NodeType.TEMP_TABLE, [ParseTreeNode(input_tables[1])])
    ren1_expr = ParseTreeNode(NodeType.RENAME_TABLE, [table1_expr, ParseTreeNode("X")])
    ren2_expr = ParseTreeNode(NodeType.RENAME_TABLE, [table2_expr, ParseTreeNode("Y")])
    join_expr = ParseTreeNode(NodeType.INPUT2, [ren1_expr, ren2_expr])
    colspec1_expr = ParseTreeNode(NodeType.COLSPEC, [ParseTreeNode("X"), ParseTreeNode("domain")])
    colspec2_expr = ParseTreeNode(NodeType.COLSPEC, [ParseTreeNode("Y"), ParseTreeNode("codomain")])
    eq_expr = ParseTreeNode(NodeType.EQUALS, [colspec1_expr, colspec2_expr])
    cond_expr = ParseTreeNode(NodeType.CONDITION, [join_expr, eq_expr])
    colspeclist_expr = ParseTreeNode(NodeType.COLSPECLIST, [
        ParseTreeNode(NodeType.COLSPEC, [ParseTreeNode("Y"), ParseTreeNode("domain")]),
        ParseTreeNode(NodeType.COLSPEC, [ParseTreeNode("X"), ParseTreeNode("codomain")])
    ])
    proj_expr = ParseTreeNode(NodeType.PROJECTION, [cond_expr, colspeclist_expr])
    assign_expr = ParseTreeNode(NodeType.ASSIGN, [proj_expr, ParseTreeNode(output_table)])
    return assign_expr


# def make_select_expr(columns, columns_alias, result_name, table_name, table_alias):

#     table_expr = ParseTreeNode(NodeType.TABLE, [ParseTreeNode(table_name), ParseTreeNode(table_alias)])
#     colspecs_list = [ ParseTreeNode(NodeType.COLSPEC, [ParseTreeNode(table_alias), ParseTreeNode(column)]) for column in columns ]
#     colspeclist_expr = ParseTreeNode(NodeType.COLSPECLIST, colspecs_list)
#     projection_expr = ParseTreeNode(NodeType.PROJECTION, [table_expr, colspeclist_expr])
#     rename_expr = projection_expr
#     for (column, alias) in zip(columns, columns_alias):
#         if alias is not None:
#             colspec_expr = ParseTreeNode(NodeType.COLSPEC, [ParseTreeNode(table_alias), ParseTreeNode(column)])
#             rename_expr = ParseTreeNode(NodeType.RENAME, [rename_expr, ParseTreeNode(alias), colspec_expr])
#     assign_expr = ParseTreeNode(NodeType.ASSIGN, [rename_expr, ParseTreeNode(result_name)])    
#     return assign_expr


def make_select_expr(columns, column_aliases, result_name, table_name, table_alias):

    table = TableNode(table_name, table_alias)
    projection = ProjectionNode(table)
    projection.add_columns(table_alias, columns)
    rename = RenameNode(projection)
    rename.add_columns(table_alias, columns, column_aliases)
    assign = AssignNode(rename, result_name)

    return assign


def test_InterParseTree():
    t1 = InterParseTree("woont_op")
    t2 = InterParseTree("o(ligt_in,woont_op)")
    t3 = InterParseTree("o(woont_op)")
    t4 = InterParseTree("o(onderdeel_van,ligt_in,woont_op)")
    t5 = InterParseTree("o(i(onderdeel_van,ligt_in),woont_op)")
    t6 = InterParseTree("l(aa,bb)") # Syntax Error: operator l() unknown
    print(t1)


def test_BFS():
    t5 = InterParseTree("o(ligt_in,woont_op)")
    t5.generate_ralg_expr()


def test_rename_node():

    r = RenameNode()
    r.add_columns("A", ["id", "gemeente"], ["domain", "codomain"])
    s = RenameNode()
    s.add_columns("A", ["persoons_id", "woonadres"], ["id", "adres"])

    r.combine(s)
    return None


def test_projection_node():

    p = ProjectionNode()
    p.add_columns("tbl_persoon", ["persoons_id", "gemeente"])
    print(p)

    q = ProjectionNode()
    q.add_columns("tbl_persoon", ["persoons_id", "adres"])

    p.combine(q)

    r = RenameNode()
    r.add_columns("A", ["id", "gemeente"], ["domain", "codomain"])
    print(r)

    s = ProjectionNode()
    s.add_columns("A", ["domain", "codomain", "comment"])

    s.combine(r)
    r.add_child(s)
    print(r)

    return None


def test_generate_ralg_expr():

    t = InterParseTree("woont_op")
    t.generate_ralg_expr()


test_generate_ralg_expr()

