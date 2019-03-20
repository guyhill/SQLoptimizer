class name():
    def __init__(self, first, last):
        self.first = first
        self.last = last
    def __eq__(self, other):
        return self.first == other.first and self.last == other.last

x = name("Guido", "Van den Heuvel")
y = name("Joost", "Van den Heuvel")
z = name("Guido", "Van den Heuvel")
w = name("Rivka", "Van den Heuvel")

l = [x, y]

print(id(x))
print(id(y))
print(id(z))

print(x in l)
print(z in l)

print(l.index(x))
print(l.index(z))
print(l.index(w))