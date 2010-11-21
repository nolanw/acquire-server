# Game-manipulating functions. (Games are just dicts so they can be easily 
# passed around and serialized and such.)

from random import shuffle

class GameError(Exception):
    """Superclass for all exceptions in the gametools module."""
    pass

class GameAlreadyStartedError(GameError):
    pass

class GamePlayNotAllowedError(GameError):
    pass

#### Game creation

def new_game():
    """Factory for new games. Sets up the basic attributes."""
    return {'players': [], 'started': False, 'ended': False}


#### Players

def player_named(game, player_name):
    """Find the player with the given name.
    
    Returns:
        - The player dict if the player named is in the game.
        - None if the player named is not in the game.
    """
    for player in game['players']:
        if player['name'] == player_name:
            return player
    return None

def add_player_named(game, player_name):
    """If possible, add a new player named player_name to the game.
    
    May raise GameAlreadyStartedError.
    """
    if game['started']:
        raise GameAlreadyStartedError()
    if not player_named(game, player_name):
        game['players'].append({'name': player_name})

def remove_player_named(game, player_name):
    """If possible, remove the player named player_name from the game.
    
    May raise GameAlreadyStartedError.
    """
    if game['started']:
        raise GameAlreadyStartedError()
    game['players'].remove(player_named(game, player_name))


#### Game setup

def start_game(game):
    """Do all the setup of the game.
    
    Returns a mapping of starting tiles to the players who drew them.
    """
    if not game['players']:
        raise GameError('cannot start a game with no players')
    
    hotel_names = ['sackson', 'zeta', 'america', 'fusion', 'hydra', 'quantum', 
                   'phoenix']
    game['hotels'] = map(lambda h: {'name': h, 'tiles': []}, hotel_names)
    
    game['tilebag'] = [str(i) + a for i in range(1, 13) for a in 'ABCDEFGHI']
    shuffle(game['tilebag'])
    
    # To figure out the starting player, everyone draws one tile from the bag 
    # and puts it on the board. The player who drew the tile closest to row A 
    # goes first, with ties broken by the tile closest to column 1.
    starting_tiles = {}
    for player in game['players']:
        starting_tiles[game['tilebag'].pop()] = player
    starting_order = starting_tiles.keys()
    starting_order.sort(key=lambda t: t[-1] + t[:-1])
    starting_player = starting_tiles[starting_order[0]]
    shuffle(game['players'])
    game['players'].remove(starting_player)
    game['players'].insert(0, starting_player)
    game['lonely_tiles'] = starting_order
    
    for player in game['players']:
        player['rack'] = game['tilebag'][:6]
        del game['tilebag'][:6]
        player['shares'] = {}
    
    game['action_queue'] = []
    append_action(game, 'play_tile', starting_player)
    
    game['started'] = True
    return starting_tiles


#### Hotels

def hotel_named(game, hotel_name):
    """Find the hotel with the given name.
    
    Returns the dict for the associated hotel, or None if no such hotel.
    """
    for hotel in game['hotels']:
        if hotel['name'] == hotel_name:
            return hotel
    return None

def bank_shares(game, hotel):
    """Returns the number of shares in the bank for the given hotel."""
    return 25 - sum(p['shares'].get(hotel['name'], 0) for p in game['players'])


#### Action queue
#
# The action queue of a game tracks which player is to play next. It's a queue, 
# rather than just a single value, because hotel mergers result in several 
# subsequent actions that cannot be computed along the way.

def append_action(game, action, player):
    """Append an action to the game's action queue which must be performed by 
    the given player.
    """
    game['action_queue'].append(dict(action=action, player=player['name']))


#### Playing tiles

def play_tile(game, player, tile):
    """If allowed, play tile from player's rack on to the board. Any new hotels 
    or mergers are taken care of.
    """
    if tile not in player['rack']:
        raise GamePlayNotAllowedError('must play tiles from tile rack')
    
    player['rack'].remove(tile)
    game['lonely_tiles'].append(tile)
    player['rack'].append(game['tilebag'].pop())
