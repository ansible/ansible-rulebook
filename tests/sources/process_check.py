import psutil
import time


def main(queue, args):

    names = args.get("names", None)

    original_processes = {p.pid: p.name() for p in psutil.process_iter()}
    if names is not None:
        original_processes = {
            pid: name for pid, name in original_processes.items() if name in names
        }

    while True:
        time.sleep(1)
        current_processes = {p.pid: p.name() for p in psutil.process_iter()}
        if names is not None:
            current_processes = {
                pid: name for pid, name in current_processes.items() if name in names
            }
        new_processes = set(current_processes.keys()) - set(original_processes.keys())
        lost_processes = set(original_processes.keys()) - set(current_processes.keys())
        for new in new_processes:
            queue.put(
                dict(
                    process_check=dict(
                        pid=new, name=current_processes[new], status="running"
                    )
                )
            )
        for lost in lost_processes:
            queue.put(
                dict(
                    process_check=dict(
                        pid=lost, name=original_processes[lost], status="stopped"
                    )
                )
            )
        original_processes = current_processes


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), {})
