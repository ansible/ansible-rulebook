

def lookup(lookup_type, *args):
    if lookup_type in lookups:
        return lookups[lookup_type](*args)


def lookup_file(location):
    with open(location) as f:
        return f.read().strip()


lookups = dict(file=lookup_file)
