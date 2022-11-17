#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os

from watchdog.events import RegexMatchingEventHandler
from watchdog.observers import Observer


def main(queue, args):

    log_file_patterns = {
        os.path.abspath(log_file): patterns
        for log_file, patterns in args.get("log_file_patterns", {}).items()
    }
    log_file_locs = {log_file: 0 for log_file in log_file_patterns}

    for log_file in log_file_locs:
        with open(log_file) as f:
            f.seek(0, os.SEEK_END)
            log_file_locs[log_file] = f.tell()

    print(log_file_locs)

    if not log_file_patterns:
        return

    class Handler(RegexMatchingEventHandler):
        def __init__(self, **kwargs):
            RegexMatchingEventHandler.__init__(self, **kwargs)

        def on_created(self, event):
            pass

        def on_deleted(self, event):
            pass

        def on_modified(self, event):
            if event.src_path in log_file_patterns:
                with open(event.src_path) as f:
                    f.seek(log_file_locs[event.src_path])
                    new_data = f.readlines()
                    print(new_data)
                    log_file_locs[event.src_path] = f.tell()
                for pattern in log_file_patterns[event.src_path]:
                    for line in new_data:
                        if pattern in line:
                            queue.put(
                                dict(
                                    log_scraper=dict(
                                        pattern=pattern,
                                        log_file=event.src_path,
                                        line=line,
                                    )
                                )
                            )

        def on_moved(self, event):
            pass

    observer = Observer()
    handler = Handler()

    for log_file in log_file_patterns:
        directory = os.path.dirname(log_file)
        observer.schedule(handler, directory, recursive=False)

    observer.start()

    try:
        observer.join()
    finally:
        observer.stop()


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), {"log_file_patterns": {"test.log": ["ERROR"]}})
