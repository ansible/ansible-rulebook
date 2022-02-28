
def main(queue, args):

    for i in range(int(args['limit'])):
        queue.put(dict(i=i))
