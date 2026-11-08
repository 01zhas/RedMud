"""Internal budgets shared by native definitions and dictionary conversion."""
MAX_DEPTH = 64
CONFIG_DEPTH = MAX_DEPTH * 4 + 8


class DepthLimit(ValueError):
    def __init__(self, path):
        self.path = path
        super().__init__('Depth limit exceeded')


def check_config(value):
    # Iterative preflight before json.dumps to avoid Python recursion failures.
    stack = [(value, 1, False)]
    active = set()
    while stack:
        current, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(current))
            continue
        if depth > CONFIG_DEPTH:
            raise ValueError('Invalid execution plan')
        if isinstance(current, (dict, list, tuple)):
            if id(current) in active:
                raise ValueError('Invalid execution plan')
            active.add(id(current))
            stack.append((current, depth, True))
            if isinstance(current, dict):
                if any(not isinstance(k, str) for k in current):
                    raise ValueError('Invalid execution plan')
                children = current.values()
            else:
                children = current
            stack.extend((item, depth+1, False) for item in children)
