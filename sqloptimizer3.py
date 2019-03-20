class ParseTreeNode:
    def __init__(self, children):
        self.children = children

class TableNode(ParseTreeNode):
    def __init__(self, tablename, table_alias):
        self.tablename = tablename
        self.table_alias = table_alias
        super().__init__(None)

class ProjectionNode(ParseTreeNode):
    def __init__(self, )