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
        self.log.debug("New client from %s:%d." % address)
    
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
            self.set_client_state(client, 3)
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
        cited = '%s: %s' % (message['player'], message['chat_message'])
        self.send_to_all_clients(Directive('LM', cited))
    
    def game_chat_message(self, message):
        """A chat message destined for players of a certain game."""
        cited = '%s: %s' % (message['player'], message['chat_message'])
        self.send_to_clients_in_game(message['game'], Directive('GM', cited))
    
    
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
            self.set_client_state(client, 4)
            self.set_client_state(client, 5)
        announcement = '* %s has started new game %d.' % (player, 
                                                          game['number'])
        self.send_to_all_clients(Directive('LM', announcement))
        self.update_game_views(game)
    
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
            self.set_client_state(client, 4)
        announcement = '* %s has joined game %d.' % (player, game['number'])
        self.send_to_all_clients(Directive('LM', announcement))
        announcement = '* %s has joined the game.' % player
        self.send_to_clients_in_game(game, Directive('GM', announcement))
        self.update_game_views(game)
    
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
            self.set_client_state(client, 3)
        client = self.client_named(gametools.host(game))
        if client:
            self.set_client_state(client, 5)
        announcement = '* %s has left game %d.' % (player, game['number'])
        self.send_to_all_clients(Directive('LM', announcement))
        self.update_game_views(game)
    
    def PG_directive(self, client, directive):
        """The client would like to start game play in an active game."""
        self.send_to_backend('play_game', player=self.name_of_client(client))
    
    def play_game_message(self, message):
        """Someone started a game. Tell everyone who needs to know."""
        game = message['game']
        announcement = '* Game %d has begun!' % game['number']
        self.send_to_all_clients(Directive('LM', announcement))
        
        # Send all of these directives in one chunk so Acquire.app correctly 
        # parses the directives.
        directives = [Directive('GM', '* The game has begun!')]
        for start_tile, player in message['start_tiles'].iteritems():
            name = player['name']
            client = self.client_named(name)
            if client:
                self.set_client_state(client, 6)
            announcement = '* %s drew start tile %s' % (name, start_tile)
            directives.append(Directive('GM', announcement))
        self.send_to_clients_in_game(game, ''.join(str(d) for d in directives))
        self.update_game_views(game)
    
    def game_over_message(self, message):
        """A game ended."""
        announcement = '* Game %d has ended.' % message['game_number']
        self.send_to_all_clients(Directive('LM', announcement))
    
    
    #### Playing games.
    
    def PT_directive(self, client, directive):
        """A client wants to play a tile."""
        try:
            i = int(directive[0]) - 1
            tile = self.client_racks[client.fileno()][i]
        except IndexError, ValueError:
            log.debug('failed Play Tile for client %d: %s', client.fileno(), 
                      directive)
        self.send_to_backend('play_tile', tile=tile, 
                             player=self.name_of_client(client))
    
    def tile_played_message(self, message):
        """Someone played a tile."""
        announcement = '* %(player)s played tile %(tile)s.' % message
        game = message['game']
        self.send_to_clients_in_game(game, Directive('GM', announcement))
        self.update_game_views(game)
    
    
    #### Error messages

    def error_message(self, message):
        """Deliver the error to the addressed client, if that client is of this 
        frontend.
        """
        client = self.client_named(message['player'])
        if client:
            announcement = 'E;%s;%s' % (message['error'], message['detail'])
            self.send_to_client(client, Directive('M', announcement))
            client_state = self.state_of_client(client)
            
            # Send a Set State directive so NetAcquire doesn't wait for a 
            # response to a failed request that may have been the source of the 
            # error. (For example, if a player attempts to join a nonexistent 
            # game and this SS directive isn't sent, they cannot attempt to 
            # join *any* games.)
            self.send_to_client(client, Directive('SS', client_state))
    
    
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
        self.client_states = {}
        self.client_racks = {}
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
    
    def state_of_client(self, client):
        """Returns the most recently set state for the given client (appropriate 
        to include in a Set State directive), or 3 if no recent state is known.
        """
        if client.fileno() in self.client_states:
            return self.client_states[client.fileno()]
        else:
            return 3
    
    def set_client_state(self, client, state):
        """Sends a Set State directive to the client and remembers the state for 
        later.
        """
        self.client_states[client.fileno()] = int(state)
        self.send_to_client(client, Directive('SS', int(state)))
    
    def set_client_rack(self, client, new_rack):
        """Updates the client's rack, preserving indices for unchanging tiles.
        
        This is done in-place (i.e. a tile at index 4 is always there until 
        removed) because otherwise NetAcquire won't highlight the tile on the
        board.
        """
        fileno = client.fileno() 
        if fileno in self.client_racks:
            old_rack = self.client_racks[fileno]
            if old_rack:
                rack = [t if t in new_rack else None for t in old_rack]
            else:
                rack = new_rack
            added = [t for t in new_rack if t not in rack]
            for tile in added:
                rack[rack.index(None)] = tile
            new_rack = rack
        self.client_racks[fileno] = new_rack
    
    @classmethod
    def tile_id(cls, tile):
        """Returns the NetAcquire Tile-ID of the given tile.
        
        Tile-IDs start at 1 (tile 1A) and increase down the column (i.e. tile 
        1I has a Tile-ID of 9), then to the top of the next column (i.e. tile 
        2A has a Tile-ID of 10), and so on.
        """
        return (int(tile[:-1]) - 1) * 9 + ord(tile[-1]) - ord('A') + 1
    
    @classmethod
    def hotel_id(cls, hotel_name):
        """Returns the NetAcquire Hotel-ID of the hotel with the given name."""
        ids = (0x0000FF, 0x00FFFF, 0xFF0000, 0x00FF00, 0x004080, 0xFFFF00, 
               0xFF00FF)
        return dict(zip(gametools.hotel_names, ids))[hotel_name]
    
    def update_game_views(self, game):
        """Sends a series of Set Value and other directives to all clients of 
        this frontend who are in game so that their game views represent the 
        given game.
        """
        for player in game['players']:
            client = self.client_named(player['name'])
            if client:
                self.update_scoreboard_view(client, game)
                self.update_board(client, game)
                self.set_client_rack(client, player.get('rack', []))
                self.update_rack(client, game)
        if game['started'] and not game['ended']:
            self.update_action_queue(game)
    
    def update_scoreboard_view(self, client, game):
        """Sends a series of Set Value directives to the given client so that 
        its scoreboard represents the given game's.
        """
        template = Directive('SV', 'frmScoreSheet', 'lblData', 0, 'Caption', '')
        send = lambda: self.send_to_client(client, template)
        for i, player in enumerate(game['players']):
            template[2] = i + 1
            template[4] = player['name']
            send()
            if game['started']:
                template[2] = i + 82
                template[4] = player['cash']
                send()
                for j, hotel_name in enumerate(gametools.hotel_names):
                    template[2] = (33, 40, 47, 54, 61, 68, 75)[j] + i
                    template[4] = player['shares'][hotel_name] or ' '
                    send()
        for i in xrange(len(game['players']), 7):
            template[2] = i + 1
            template[4] = ' '
            send()
        if game['started']:
            for i, hotel_name in enumerate(gametools.hotel_names):
                hotel = gametools.hotel_named(game, hotel_name)
                template[2] = 9 + i
                template[4] = gametools.bank_shares(game, hotel)
                send()
                template[2] = 17 + i
                template[4] = len(hotel['tiles']) or '-'
                send()
                template[2] = 25 + i
                template[4] = gametools.share_price(hotel) / 100 or '-'
                send()
    
    def update_board(self, client, game):
        """Sends a series of Set Board directives to the given client so that 
        its board represents the given game's.
        """
        template = Directive('SB', 0, 0)
        send = lambda: self.send_to_client(client, template)
        for tile in game.get('lonely_tiles', []):
            template[0] = self.tile_id(tile)
            template[1] = 0
            send()
        for hotel in game.get('hotels', []):
            template[1] = self.hotel_id(hotel['name'])
            for tile in hotel['tiles']:
                template[0] = self.tile_id(tile)
                send()
    
    def update_rack(self, client, game):
        """Sends a series of Activate Tile directives to the given client so 
        that its tile rack represents the one saved by this frontend.
        """
        if game['started']:
            unplayable = gametools.tiles_that_merge_safe_hotels(game)
            if not gametools.hotels_off_board(game):
                unplayable.extend(gametools.tiles_that_create_hotels(game))
        else:
            unplayable = []
        for i, tile in enumerate(self.client_racks[client.fileno()]):
            if tile:
                if tile in unplayable:
                    chain_id = 0x606060
                else:
                    chain_id = 0xC0C0C0
                directive = Directive('AT', i + 1, self.tile_id(tile), chain_id)
            else:
                directive = Directive('SV', 'frmTileRack', 'cmdTile', i + 1,
                                      'Visible', 0)
            self.send_to_client(client, directive)
    
    def update_action_queue(self, game):
        """Routes to a dedicated method for handling the first action in the 
        given game's action queue.
        """
        first_action = game['action_queue'][0]['action']
        handler_name = first_action + '_action'
        if hasattr(self, handler_name):
            try:
                getattr(self, handler_name)(game)
            except Exception:
                self.log.exception('action_queue handler bailed')
        else:
            self.log.debug('unimplemented action %s', first_action)
    
    def play_tile_action(self, game):
        """It's a new player's turn, and they need to play a tile."""
        active_player_name = game['action_queue'][0]['player']
        # Active player gets a nice salmon background.
        template = Directive('SV', 'frmScoreSheet', 'lblData', 0, 
                             'BackColor', 0)
        directives = []
        for i, player in enumerate(game['players']):
            template[2] = i + 1
            if player['name'] == active_player_name:
                template[4] = 0xC0C0FF
            else:
                template[4] = 0xFFFFFF
            directives.append(str(template))
        directives.append(str(Directive('GM', "*** %s's turn." % 
                                              active_player_name)))
        directives.append(str(Directive('GM', "*Waiting for %s to play tile" % 
                                              active_player_name)))
        self.send_to_clients_in_game(game, ''.join(directives))
        client = self.client_named(active_player_name)
        if client:
            self.send_to_client(client, Directive('GT'))
    
    def disconnected(self, client):
        """A client disconnected, so forget all about them."""
        fileno = client.fileno()
        if fileno in self.names:
            self.send_to_backend('logout', player=self.names[fileno])
        client_collections = [self.client_queues, self.names, self.clients, 
                              self.shaking_hands, self.client_states, 
                              self.client_racks]
        for collection in client_collections:
            if fileno in collection:
                del collection[fileno]
        self.remove_fileno(self.inputs, fileno)
        client.close()
        self.log.debug('client %d has disconnected', fileno)
    

if __name__ == '__main__':
    NetAcquire().run()
