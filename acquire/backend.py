# Runs games, player login, and chat using Acquire messages (dicts with a 
# 'path' key).

import logging
import Queue
import sys
import zmq

class Backend(object):
    """Run games of Acquire, log players in and out, and move chat messages."""
    
    def __init__(self):
        self.log = logging.getLogger('Backend')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.StreamHandler())
    
    def run(self, pub_address="tcp://127.0.0.1:16180", 
            pull_address="tcp://127.0.0.1:27183"):
        """Start the backend, with PUB and PULL sockets on the given addresses.
        """
        # Socket setup.
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(pub_address)
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(pull_address)
        self.log.info("Acquire backend is listening on %s", pull_address)
        self.log.info("                 and sending on %s", pub_address)
        self.log.info("Press CTRL-D to exit.")
        
        # Queue and collection setup.
        self.pub_queue = Queue.Queue()
        self.players = set()
        self.games = {}
        
        # Listen forever until end of file (CTRL-D on *nix) seen on stdin.
        while True:
            self._runloop()
    
    def _runloop(self):
        """A single run-through of all sockets handled by this backend."""
        inputs = [self.pull_socket, sys.stdin]
        outputs = [] if self.pub_queue.empty() else [self.pub_socket]
        exceptionals = inputs + [self.pub_socket]
        read, write, error = zmq.select(inputs, outputs, exceptionals)
        for fileno in read:
            if fileno == self.pull_socket:
                self.route_message(self.pull_socket.recv_json())
            elif fileno == sys.stdin.fileno():
                for _ in sys.stdin:
                    pass
                sys.exit(0)
        for fileno in write:
            if fileno == self.pub_socket:
                try:
                    self.pub_socket.send_json(self.pub_queue.get_nowait())
                except Queue.Empty:
                    pass
        for fileno in error:
            if fileno == self.pub_socket:
                raise Exception('PUB socket in exceptional state')
            elif fileno == self.pull_socket:
                raise Exception('PULL socket in exceptional state')
            elif fileno == sys.stdin.fileno():
                raise Exception('stdin in exceptional state')
    
    def route_message(self, message):
        """Pass message along to a path-specific handler."""
        handler_name = message['path'] + '_message'
        if hasattr(self, handler_name):
            try:
                getattr(self, handler_name)(message)
            except Exception:
                self.log.exception('error handling %s message', message['path'])
        else:
            self.log.debug('unimplemented message %s', message['path'])
    
    def send_to_frontends(self, path, **message):
        """Send a message with the given path and key-value pairs to the 
        frontends.
        """
        message.update(dict(path=path))
        self.pub_queue.put(message)
    
    def login_message(self, message):
        """A player wants to log in. Deny them if another player by that name 
        has already logged in.
        """
        player = message['player']
        if player in self.players:
            self.send_to_frontends('duplicate_name', player=player)
            self.log.debug('Already have a player named %s', player)
        else:
            self.players.add(player)
            self.send_to_frontends('logged_in', player=player)
            self.log.debug('Hello %s!', player)
    
    def logout_message(self, message):
        """A player has left."""
        player = message['player']
        self.players.discard(player)
        self.log.debug('Goodbye %s', player)
    

if __name__ == '__main__':
    Backend().run()
