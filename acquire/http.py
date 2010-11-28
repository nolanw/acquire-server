import sys
import zmq
from mongrel2.handler import Connection, CTX

sender_id = "d693a7cc-2bba-469a-b478-11a50ca09116"
conn = Connection(sender_id, "tcp://127.0.0.1:9999", "tcp://127.0.0.1:9998")
clients = {}
names = {}
senders = {}
logging_in = {}

backend_push = CTX.socket(zmq.PUSH)
backend_push.connect("tcp://127.0.0.1:27183")
backend_sub = CTX.socket(zmq.SUB)
backend_sub.connect("tcp://127.0.0.1:16180")
backend_sub.setsockopt(zmq.SUBSCRIBE, '')

def client_message(req, message):
    print "client_message:", message
    path = message['path']
    if req.conn_id in clients:
        message.update({'player': clients[req.conn_id]})
    elif path == 'login':
        logging_in[message['player']] = req.conn_id
    else:
        print 'unknown client sending non-login message'
        return
    senders[req.conn_id] = req.sender
    backend_push.send_json(message)

broadcast = """logged_in lobby_chat games_list started_game joined_game 
               left_game game_over""".split()
game = """play_game tile_played hotel_created survivor_chosen shares_disbursed 
          purchased""".split()

def backend_message(message):
    print "backend_message:", message
    path = message['path']
    if path == 'logged_in':
        name = message['player']
        if name in logging_in:
            conn_id = logging_in[name]
            del logging_in[name]
            clients[conn_id] = name
    elif path == 'duplicate_name':
        name = message['player']
        if name in logging_in:
            conn_id = logging_in[name]
            conn.deliver_json(senders[conn_id], [conn_id], message)
            del logging_in[name]
            return
    if path in broadcast:
        conn.deliver_json(sender_id, clients.keys(), message)
    elif path in game:
        conn_ids = map(lambda p: names[p['name']], message['game']['players'])
        conn.deliver_json(sender_id, conn_ids, message)
    elif 'player' in message:
        conn_id = names[message['player']]
        conn.deliver_json(senders[conn_id], [conn_id], message)
    else:
        print 'cannot deliver message'


poller = zmq.Poller()
poller.register(backend_sub, zmq.POLLIN)
poller.register(conn.reqs, zmq.POLLIN)
poller.register(sys.stdin, zmq.POLLIN)

print "Acquire mongrel2 handler is up. Press CTRL-D to exit."

while True:
    ready = [a for a, _ in poller.poll()]
    if conn.reqs in ready:
        try:
            req = conn.recv_json()
            client_message(req, req.data)
        except Exception, e:
            print 'failed reading client message:', e
    if backend_sub in ready:
        try:
            backend_message(backend_sub.recv_json())
        except:
            print 'failed reading backend message'
    if sys.stdin.fileno() in ready:
        for _ in sys.stdin:
            pass
        sys.exit(0)
