import zmq
import numpy as np
import time

class zmqPublisher:
    """Publishes a python dictionary on a port with a given topic."""

    def __init__(self, port=5550, topic='test'):
        zmq_context = zmq.Context()
        self.topic = topic
        self.pub_socket = zmq_context.socket(zmq.PUB)
        self.pub_socket.setsockopt(zmq.LINGER, 100) #100 ms after the socket is closed it will clear the buffer
        self.pub_socket.bind("tcp://*:%s" % port)
        print('Broadcasting on port {0} with topic {1}'.format(port,topic))


    def close(self):
        self.pub_socket.close()

    def publish_data(self,data,prnt=False):
        try:
            timestamp = time.time()
            data = str(data).strip('(').strip(')')
            send_string = "%s, %f, %s" % (self.topic, timestamp, data)
            if prnt: print(send_string)
            self.pub_socket.send_string(send_string, flags=0, encoding='utf-8') #python3
            #self.pub_socket.send(send_string) #python2
        except Exception as e:
            print('error retrieving/parsing data')
            print(e)

    def test_stream(self):
        while(True):
            try:
                newval1 = np.random.rand()
                newval2 = np.random.rand()
                data = (newval1,newval2)
                self.publish_data(data)
            except KeyboardInterrupt:
                break
            time.sleep(1)

#publisher = zmq_pub_dict()
#publisher.test_stream()