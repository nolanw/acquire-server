# Runs games, player login, and chat using Acquire messages (dicts with a 
# 'path' key).

import logging
import Queue
import sys
import zmq

from acquire import gametools

class Backend(object):
    """Run games of Acquire, log players in and out, and move chat messages."""
    
    #### Logging in and out.
    
    def login_message(self, message):
        """A player wants to log in. Deny them if another player by that name 
        has already logged in.
        """
        player = message['player']
        if player in self.players:
            self.send_to_frontends('duplicate_name', player=player)
            self.log.debug('Already have a player named %s.', player)
        else:
            self.players.add(player)
            self.send_to_frontends('logged_in', player=player)
            self.log.debug('Hello %s!', player)
    
    def logout_message(self, message):
        """A player has left."""
        player = message['player']
        self.players.discard(player)
        self.log.debug('Goodbye %s', player)
    
    
    #### Chat.

    def lobby_chat_message(self, message):
        """Someone wants to talk to the lobby."""
        del message['path']
        self.send_to_frontends('lobby_chat', **message)
    
    
    #### Listing, starting, joining, leaving, and starting play of games.
    
    def games_list_message(self, message):
        """Someone wants a list of all active games."""
        self.send_games_list_to_frontends()
    
    def start_game_message(self, message):
        """Someone's starting a new game."""
        player = message['player']
        game = self.game_for_player(player)
        if game:
            error = 'Already in game'
            detail = ('Please leave your current game before '
                      'starting a new one.')
            self.send_to_frontends('error', player=player, error=error, 
                                   detail=detail)
        else:
            game = gametools.new_game(self.next_game_number())
            gametools.add_player_named(game, player)
            self.games_list.append(game)
            self.send_to_frontends('started_game', player=player, game=game)
            self.send_games_list_to_frontends()
            self.log.debug('Game %d started by %s.', game['number'], player)
    
    def leave_game_message(self, message):
        """Someone wants to leave their game."""
        player = message['player']
        game = self.game_for_player(player)
        if game:
            try:
                gametools.remove_player_named(game, player)
                self.send_to_frontends('left_game', player=player, game=game)
                self.log.debug('%s left game %d.', player, game['number'])
            except gametools.GameAlreadyStartedError:
                error = 'Game has started'
                detail = ('You cannot leave a game that has already started.')
                self.send_to_frontends('error', player=player, error=error, 
                                       detail=detail)
            if not game['players']:
                self.games_list.remove(game)
                self.send_to_frontends('game_over', game_number=game['number'])
            self.send_games_list_to_frontends()
    
    
    #### Helpers
    
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
        self.games_list = []
        
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
    
    def next_game_number(self):
        """Returns a unique game number."""
        try:
            self._next_game_number += 1
        except AttributeError:
            self._next_game_number = 1
        return self._next_game_number
    
    def send_games_list_to_frontends(self):
        """Send the list of games to the frontends."""
        self.send_to_frontends('games_list', games_list=self.games_list)
    
    def game_for_player(self, player_name):
        """Returns the game that the named player is currently in, or None if 
        there is no such game.
        """
        for game in self.games_list:
            if player_name in map(lambda p: p['name'], game['players']):
                return game
        return None
    

if __name__ == '__main__':
    Backend().run()
