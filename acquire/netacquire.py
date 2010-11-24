# Accepts connections from NetAcquire clients and translates between NetAcquire
# directives and Acquire messages.

import logging
import Queue
import socket
import sys
import zmq

from acquire.directive import Directive

class NetAcquire(object):
    """Accept NetAcquire client connections and translate between directives 
    and messages.
    """
    
    def __init__(self):
        self.log = logging.getLogger('NetAcquire')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.StreamHandler())
    
    def run(self, server_name='Acquire', accept_address=('localhost', 31415), 
            backend_push_address='tcp://localhost:27183', 
            backend_sub_address='tcp://localhost:16180'):
        """Start accepting clients and connect to the backend."""
        
        # Socket setup.
        self.log.info("NetAcquire frontend starting. Press CTRL-D to exit.")
        self.context = zmq.Context()
        self.backend_push = self.context.socket(zmq.PUSH)
        self.backend_push.connect(backend_push_address)
        self.backend_sub = self.context.socket(zmq.SUB)
        self.backend_sub.connect(backend_sub_address)
        self.backend_sub.setsockopt(zmq.SUBSCRIBE, '')
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(accept_address)
        self.server.listen(5)
        self.log.info("Listening on %s:%d" % accept_address)
        
        # Queue, select, and announce setup.
        self.inputs = [self.server, self.backend_sub, sys.stdin]
        self.backend_queue = Queue.Queue()
        self.clients = {}
        self.client_queues = {}
        self.announce = Directive("SP", "2", "0", "4", str(server_name))
        
        # Listen forever until end of file (CTRL-D on *nix) seen on stdin.
        while True:
            self._runloop()
    
    def _runloop(self):
        """A single run-through of all sockets handled by this frontend."""
        outputs = [] if self.backend_queue.empty() else [self.backend_push]
        read, write, error = zmq.select(self.inputs, outputs, self.inputs)
        for fileno in read:
            if fileno == self.backend_sub:
                self.route_message(self.backend_sub.recv_json())
            elif fileno == self.server.fileno():
                self.start_handshake()
            elif fileno == sys.stdin.fileno():
                for _ in sys.stdin:
                    pass
                sys.exit(0)
            elif fileno in self.clients:
                client = self.clients[fileno]
                data = client.recv(4096)
                if data:
                    self.route_directives(client, data)
                else:
                    self.disconnected(client)
            else:
                log.warning('unknown input file descriptor %r', fileno)
                self.remove_fileno(self.inputs, fileno)
        
        for fileno in write:
            if fileno == self.backend_push:
                try:
                    message = self.backend_queue.get_nowait()
                except Queue.Empty:
                    continue
                self.backend_push.send_json(message)
            elif fileno in self.clients:
                try:
                    directives = self.client_queues[fileno].get_nowait()
                except Queue.Empty:
                    continue
                self.clients[fileno].send(directives)
            else:
                log.warning('unknown output file descriptor %r', fileno)
                self.remove_fileno(self.outputs, fileno)
        
        for fileno in error:
            if fileno == self.server.fileno():
                raise Exception('server socket in exceptional state')
            elif fileno == self.backend_sub:
                raise Exception('backend SUB socket in exceptional state')
            elif fileno == sys.stdin.fileno():
                raise Exception('stdin in exceptional state')
            elif fileno in self.clients:
                self.disconnected(self.clients[fileno])
    
    def start_handshake(self):
        """Accept a client connection and start shaking hands."""
        client, address = self.server.accept()
        self.clients[client.fileno()] = client
        self.inputs.append(client)
        client.send(str(self.announce))
    
    def route_directives(self, client, wiredata):
        """Parse directives from wiredata, as sent from client, and pass them 
        along to directive-specific handlers.
        """
        for directive in Directive.parse_multiple(wiredata):
            if hasattr(self, directive.code):
                getattr(self, directive.code)(client, directive)
            else:
                self.log.debug('unimplemented directive %s', directive.code)
    

if __name__ == '__main__':
    NetAcquire().run()