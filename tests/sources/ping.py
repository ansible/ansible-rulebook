
import subprocess
import time


def main(queue, args):

    ips = args.get('ips', [])
    delay = args.get('delay', 1)

    if not ips:
        return

    while True:

        for ip in ips:

            result = subprocess.call(['ping', '-c', '1', ip])
            queue.put(dict(ping=dict(ip=ip,
                                     status='up' if result == 0 else 'down',
                                     exit_code=result)))

        time.sleep(delay)




if __name__ == "__main__":
    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), {'ips': ['127.0.0.1']})


