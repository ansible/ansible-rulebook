
import pytest
import os
import multiprocessing as mp

from ansible_events.engine import run_rulesets, start_source
from ansible_events.rule_types import EventSource, EventSourceFilter

from .test_engine import new_event_loop

HERE = os.path.dirname(os.path.abspath(__file__))


def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())

def f(name):
    info('function f')
    print('hello', name)


@pytest.mark.timeout(10)
@pytest.mark.skip(reason="doesn't work in a container")
def test_process_check(new_event_loop):
    os.chdir(HERE)

    queue = mp.Queue()
    p1 = mp.Process(target=start_source,
        args=(EventSource("process_check", "process_check", dict(limit=1), [EventSourceFilter('noop', {})]),
        ["sources"],
        dict(names=['Python']),
        queue),
        daemon=True
    )
    p1.start()
    p2 = mp.Process(target=f, args=('bob',))
    p2.start()
    p2.join()

    event = queue.get()['process_check']
    print(event)

    assert event['event_type'] == 'lost_process'
    assert event['name'] == 'Python'
    assert event['status'] == 'stopped'
