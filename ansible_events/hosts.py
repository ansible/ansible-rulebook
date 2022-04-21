

from collections import defaultdict
from itertools import count

host_id_counter = count(1)

def next_host_id():
    return next(host_id_counter)

host_ids = defaultdict(next_host_id)


def get_host_id(host):
    return host_ids[host]

