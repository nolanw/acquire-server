import logging
import sys
import zmq
from mongrel2.handler import Connection, CTX

broadcast_messages = """logged_in lobby_chat games_list started_game joined_game 
                        left_game game_over logged_out""".split()
game_messages = """play_game tile_played hotel_created survivor_chosen 
                   shares_disbursed purchased""".split()

class Mongrel2Handler(object):
    """A Mongrel2 handler for Acquire."""
    
    def __init__(self, sender_id, send_spec="tcp://127.0.0.1:9999", 
                 recv_spec="tcp://127.0.0.1:9998"):
        self.sender_id = sender_id
        self.conn = Connection(sender_id, send_spec, recv_spec)
        self.clients = {}
        self.names = {}
        self.logging_in = {}
        self.log = logging.getLogger('http')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.StreamHandler())
    
    def run(self, backend_push_address="tcp://127.0.0.1:27183", 
            backend_sub_address="tcp://127.0.0.1:16180"):
        """Start the handler listening indefinitely."""
        self.backend_push = CTX.socket(zmq.PUSH)
        self.backend_push.connect("tcp://127.0.0.1:27183")
        self.backend_sub = CTX.socket(zmq.SUB)
        self.backend_sub.connect("tcp://127.0.0.1:16180")
        self.backend_sub.setsockopt(zmq.SUBSCRIBE, '')
        
        poller = zmq.Poller()
        poller.register(self.backend_sub, zmq.POLLIN)
        poller.register(self.conn.reqs, zmq.POLLIN)
        poller.register(sys.stdin, zmq.POLLIN)
        
        print "Acquire mongrel2 handler is up. Press CTRL-D to exit."
        
        while True:
            ready = [a for a, _ in poller.poll()]
            if self.conn.reqs in ready:
                try:
                    req = self.conn.recv_json()
                    if 'path' in req.data:
                        self.client_message(req, req.data)
                except Exception:
                    self.log.exception('failed reading client message:')
            if self.backend_sub in ready:
                try:
                    self.backend_message(self.backend_sub.recv_json())
                except Exception:
                    self.log.exception('failed reading backend message')
            if sys.stdin.fileno() in ready:
                for _ in sys.stdin:
                    pass
                sys.exit(0)
    
    def client_message(self, req, message):
        path = message['path']
        if req.conn_id in self.clients:
            message.update({'player': self.clients[req.conn_id]})
        elif path == 'login':
            self.logging_in[message['player']] = req.conn_id
        else:
            print 'unknown client sending non-login message'
            return
        self.backend_push.send_json(message)
    
    def backend_message(self, message):
        path = message['path']
        if path == 'logged_in':
            name = message['player']
            if name in self.logging_in:
                conn_id = self.logging_in[name]
                del self.logging_in[name]
                self.clients[conn_id] = name
                self.names[name] = conn_id
        elif path == 'duplicate_name':
            name = message['player']
            if name in self.logging_in:
                conn_id = self.logging_in[name]
                self.conn.deliver_json(self.sender_id, [conn_id], message)
                del self.logging_in[name]
                return
        elif path == 'logged_out':
            name = message['player']
            if name in self.names:
                conn_id = self.names[name]
                del self.names[name]
                del self.clients[conn_id]
        elif path == 'games_list':
            for game in message['games_list']:
                for player in game['players']:
                    if 'rack' in player:
                        del player['rack']
        if path in broadcast_messages:
            self.conn.deliver_json(self.sender_id, self.clients.keys(), message)
        elif path in game_messages:
            game = message['game']
            if 'tilebag' in game:
                del game['tilebag']
            all_tiles = dict((p['name'], p.get('rack', None)) 
                             for p in game['players'])
            for player in game['players']:
                if 'rack' in player:
                    del player['rack']
            for player in game['players']:
                try:
                    conn_id = self.names[player['name']]
                except KeyError:
                    pass
                else:
                    player['rack'] = all_tiles[player['name']]
                    self.conn.deliver_json(self.sender_id, [conn_id], message)
                    del player['rack']
        elif 'player' in message:
            try:
                conn_id = self.names[message['player']]
            except KeyError:
                pass
            else:
                self.conn.deliver_json(self.sender_id, [conn_id], message)
        else:
            print 'cannot deliver message'
    

if __name__ == '__main__':
    Mongrel2Handler('test').run()
