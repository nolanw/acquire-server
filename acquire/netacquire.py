# Accepts connections from NetAcquire clients and translates between NetAcquire
# directives and Acquire messages.

import logging
import Queue
import socket
import sys
import zmq

from acquire import gametools
from acquire.directive import Directive

class NetAcquire(object):
    """Accept NetAcquire client connections and translate between directives 
    and messages.
    """
    
    #### Handshake and logging in.
    
    def start_handshake(self):
        """Accept a client connection and start shaking hands."""
        client, address = self.server.accept()
        self.clients[client.fileno()] = client
        self.client_queues[client.fileno()] = Queue.Queue()
        self.inputs.append(client)
        client.send(str(self.announce))
        self.shaking_hands[client.fileno()] = ''
        self.log.debug("New client from %s", address[0])
    
    def PL_directive(self, client, directive):
        """The client is continuing the handshake by telling us their name."""
        if client.fileno() in self.shaking_hands:
            name = self.shaking_hands[client.fileno()] = directive[0]
            self.send_to_backend('login', player=name)
            self.log.debug('Attempting login for %s...', name)
    
    def logged_in_message(self, message):
        """Someone just logged in. Finish the handshake if it's one of this 
        frontend's clients.
        """
        client = self.handshaking_client_named(message['player'])
        if client:
            fileno = client.fileno()
            self.names[fileno] = self.shaking_hands[fileno]
            del self.shaking_hands[fileno]
            self.send_to_client(client, Directive('SS', 3))
        announcement = '* %s has entered the lobby.' % message['player']
        self.send_to_all_clients(Directive('LM', announcement))
    
    def duplicate_name_message(self, message):
        """Someone tried to log in but the name was taken. Cancel the handshake 
        if it's one of this frontend's clients.
        """
        client = self.handshaking_client_named(message['player'])
        if client:
            error = 'Duplicate user Nickname'
            detail = ("That nickname is already in use. Please pick a "
                      "different one. If you are reconnecting with the "
                      "same nickname, please wait a minute and try again.")
            client.send(str(Directive('M', '"E;%s;%s"' % (error, detail))))
            self.disconnected(client)
    
    
    #### Chat.
    
    def BM_directive(self, client, directive):
        """The client wants to send a chat message somewhere."""
        target = directive[0]
        if target == 'Lobby':
            path = 'lobby_chat'
        elif target == 'Game Room':
            path = 'game_chat'
        else:
            log.debug('unknown message target %s', target)
            return
        chat_message = Directive.unescape_param(directive[1])
        self.send_to_backend(path, chat_message=chat_message, 
                             player=self.name_of_client(client))
    
    def lobby_chat_message(self, message):
        """A chat message destined for everyone in the lobby."""
        cited_message = '%s: %s' % (message['player'], message['chat_message'])
        self.send_to_all_clients(Directive('LM', cited_message))
    
    
    #### Game listing, starting, joining, leaving, and ending.
    
    def LG_directive(self, client, directive):
        """The client would like a list of active games."""
        messages = ['# Active games: %d ...' % len(self.games_list)]
        for game in self.games_list:
            messages.append('# ->   Game #%d-> %d players, no spectators, '
                            'In Progress...' % (game['number'], 
                                                len(game['players'])))
        messages.append('# End of game list.')
        self.send_to_client(client, ''.join(str(Directive('LM', m)) 
                                    for m in messages))
    
    def games_list_message(self, message):
        """The games list changed, or someone requested an updated list."""
        self.games_list = message['games_list']
    
    def SG_directive(self, client, directive):
        """The client would like to start a new game."""
        self.send_to_backend('start_game', player=self.name_of_client(client))
    
    def started_game_message(self, message):
        """Someone started a new game. If it's a client of this frontend, get 
        them ready.
        """
        player, game = message['player'], message['game']
        client = self.client_named(player)
        if client:
            self.send_to_client(client, Directive('SS', 4))
            self.send_to_client(client, Directive('SS', 5))
        announcement = '* %s has started new game %d.' % (player, 
                                                          game['number'])
        self.send_to_all_clients(Directive('LM', announcement))
    
    def JG_directive(self, client, directive):
        """The client would like to join an active game."""
        self.send_to_backend('join_game', player=self.name_of_client(client), 
                             game_number=int(directive[0]))
    
    def joined_game_message(self, message):
        """Someone joined a game. If it's a client of this frontend, get them 
        into the game.
        """
        player, game = message['player'], message['game']
        client = self.client_named(player)
        if client:
            client.send(Directive('SS', 4))
        announcement = '* %s has joined game %d.' % (player, game['number'])
        self.send_to_all_clients(Directive('LM', announcement))
    
    def LV_directive(self, client, directive):
        """The client would like to leave an active game."""
        self.send_to_backend('leave_game', player=self.name_of_client(client))
    
    def left_game_message(self, message):
        """Someone left a game. Let our clients know who left and who is the 
        new host, if either or both are clients of this frontend.
        """
        player, game = message['player'], message['game']
        client = self.client_named(player)
        if client:
            self.send_to_client(client, Directive('SS', 3))
        client = self.client_named(gametools.host(game))
        if client:
            self.send_to_client(client, Directive('SS', 5))
        announcement = '* %s has left game %d.' % (player, game['number'])
        self.send_to_all_clients(Directive('LM', announcement))
    
    def PG_directive(self, client, directive):
        """The client would like to start game play in an active game."""
        self.send_to_backend('play_game', player=self.name_of_client(client))
    
    def play_game_message(self, message):
        """Someone started a game. Tell everyone who needs to know."""
        game = message['game']
        announcement = '* Game %d has begun!' % game['number']
        self.send_to_all_clients(Directive('LM', announcement))
        directives = [Directive('GM', '* The game has begun!')]
        for drawn_tile, player in message['starting_draws'].iteritems():
            name = player['name']
            announcement = '* %s drew starting tile %s' % (name, drawn_tile)
            directives.append(Directive('GM', announcement))
        directives.append(Directive('SS'))
        self.send_to_clients_in_game(game, ''.join(str(d) for d in directives))
    
    def game_over_message(self, message):
        """A game ended."""
        announcement = '* Game %d has ended.' % message['game_number']
        self.send_to_all_clients(Directive('LM', announcement))
    
    
    #### Disconnection and logging out.
    
    def disconnected(self, client):
        """A client disconnected, so forget all about them."""
        fileno = client.fileno()
        if fileno in self.names:
            self.send_to_backend('logout', player=self.names[fileno])
        client_collections = [self.client_queues, self.names, self.clients, 
                              self.shaking_hands]
        for collection in client_collections:
            if fileno in collection:
                del collection[fileno]
        self.remove_fileno(self.inputs, fileno)
        client.close()
        self.log.debug('client %d has disconnected', fileno)
    
    
    #### Helpers
    
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
        self.names = {}
        self.shaking_hands = {}
        self.announce = Directive("SP", "2", "0", "4", str(server_name))
        
        # Request initial game list.
        self.games_list = []
        self.send_to_backend('games_list')
        
        # Listen forever until end of file (CTRL-D on *nix) seen on stdin.
        while True:
            self._runloop()
    
    def _runloop(self):
        """A single run-through of all sockets handled by this frontend."""
        outputs = [] if self.backend_queue.empty() else [self.backend_push]
        for fileno, q in self.client_queues.iteritems():
            if not q.empty():
                outputs.append(fileno)
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
                self.log.warning('unknown input file descriptor %r', fileno)
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
    
    def route_directives(self, client, wiredata):
        """Parse directives from wiredata, as sent from client, and pass them 
        along to directive-specific handlers.
        """
        for directive in Directive.parse_multiple(wiredata):
            handler_name = directive.code + '_directive'
            if hasattr(self, handler_name):
                try:
                    getattr(self, handler_name)(client, directive)
                except Exception:
                    self.log.exception('error handling %s directive', 
                                       directive.code)
            else:
                self.log.debug('unimplemented directive %s', directive.code)
    
    def send_to_client(self, client, directive):
        """Send a directive to a client."""
        self.client_queues[client.fileno()].put(str(directive))
    
    def send_to_clients_in_game(self, game, directive):
        """Send the directive to all clients of this frontend who are in the 
        given game.
        """
        for player in game['players']:
            client = self.client_named(player['name'])
            if client:
                self.send_to_client(client, directive)
    
    def send_to_all_clients(self, directive):
        """Send a directive to all connected clients."""
        for client in self.clients.itervalues():
            self.send_to_client(client, directive)
    
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
    
    def send_to_backend(self, path, **message):
        """Send a message with the given path and key-value pairs to the 
        backend.
        """
        message.update(dict(path=path))
        self.backend_queue.put(message)
    
    def remove_fileno(self, collection, fileno):
        """Remove all objects in collection whose fileno is given."""
        to_remove = []
        for obj in collection:
            if obj == fileno or (hasattr(obj, 'fileno') and 
                                 obj.fileno() == fileno):
                to_remove.append(obj)
        for obj in to_remove:
            collection.remove(obj)
    
    def name_of_client(self, client_to_name):
        """Returns the name associated with the given client, or None if the 
        client has not finished the handshake.
        """
        for fileno, client in self.clients.iteritems():
            if client == client_to_name:
                return self.names.get(fileno, None)
        return None
    
    def handshaking_client_named(self, client_name):
        """Returns the client who is in the midst of the handshake who wants 
        the given name, or None if there is no such client.
        """
        for fileno, name in self.shaking_hands.iteritems():
            if name == client_name:
                return self.clients[fileno]
    
    def client_named(self, client_name):
        """Returns the client who calls themself the given name, or None if 
        there is no such client.
        """
        for fileno, name in self.names.iteritems():
            if name == client_name:
                return self.clients[fileno]
        return None
    

if __name__ == '__main__':
    NetAcquire().run()
