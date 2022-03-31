
def main(queue, args):

    for i in range(int(args['limit'])):
        queue.put(dict(i=i))

if __name__ == "__main__":
    class MockQueue:
        def put(self, event):
            print(event)
    main(MockQueue(), dict(limit=5))

