"""
lists_to_dicts.py:   An event filter that changes lists to dicts with integer indexes starting at 0.

For instance, the list ['a', 'b', 'c'] becomes the dict {0: 'a', 1: 'b': 2: 'c'}

"""

import multiprocessing as mp


def main(event):
    logger = mp.get_logger()
    logger.info('lists_to_dicts')
    q = []
    q.append(event)
    while q:
        o = q.pop()
        if isinstance(o, dict):
            for key in list(o.keys()):
                value = o[key]
                q.append(value)
                if isinstance(value, list):
                    del o[key]
                    o[key] = dict(zip(range(len(value)), value))
    return event
