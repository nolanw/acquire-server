# Game-manipulating functions. (Games are just dicts so they can be easily 
# passed around and serialized and such.)

from random import shuffle


hotel_names = 'sackson zeta america fusion hydra quantum phoenix'.split()


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

def active_player(game):
    """Returns the player who must perform the next action."""
    return player_named(game, game['action_queue'][0]['player'])


#### Game setup

def start_game(game):
    """Do all the setup of the game.
    
    Returns a mapping of starting tiles to the players who drew them.
    """
    if not game['players']:
        raise GameError('cannot start a game with no players')
    
    set_up_hotels(game)
    
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

def set_up_hotels(game):
    """Initialize the standard set of hotels."""
    game['hotels'] = map(lambda h: {'name': h, 'tiles': []}, hotel_names)


#### Board

def adjacent_tiles(tile):
    """Return a list of tiles that are adjacent to tile on the board."""
    col, row = int(tile[:-1]), tile[-1]
    adjacent = []
    adjacent_cols, adjacent_rows = [], []
    if col > 1:
        adjacent_cols.append(col - 1)
    if col < 12:
        adjacent_cols.append(col + 1)
    adjacent.extend(str(c) + row for c in adjacent_cols)
    if row > 'A':
        adjacent_rows.append(chr(ord(row) - 1))
    if row < 'I':
        adjacent_rows.append(chr(ord(row) + 1))
    adjacent.extend(str(col) + r for r in adjacent_rows)
    return adjacent

def where_is_tile(game, tile):
    """Return one of the following, depending on what surrounds the tile:
        - None if the tile is off the board.
        - 'lonely' if the tile is on the board but in no hotels.
        - 'sackson' or 'zeta' or ... if the tile is in a hotel.
    """
    if tile in game['lonely_tiles']:
        return 'lonely'
    for hotel in game['hotels']:
        if tile in hotel['tiles']:
            return hotel['name']
    return None

def tiles_that_create_hotels(game):
    """Return a list of tiles that, if played, would cause a new hotel to be 
    created.
    """
    tiles = []
    for on_board in game['lonely_tiles']:
        here_they_are = set(where_is_tile(game, t) 
                            for t in adjacent_tiles(on_board))
        if here_they_are & set(hotel_names):
            continue
        tiles.extend(t for t in adjacent_tiles(on_board) 
                             if t not in game['lonely_tiles'])
    return tiles

def grows_hotel(game, tile):
    """Return the hotel that would grow if tile was played, or None if no such 
    hotel exists.
    """
    nearby = set(where_is_tile(game, t) for t in adjacent_tiles(tile))
    for hotel in game['hotels']:
        if hotel['name'] in nearby:
            return hotel['name']
    return None


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

def append_action(game, action_name, player, **action):
    """Append an action to the game's action queue which must be performed by 
    the given player.
    """
    action.update(dict(action=action_name, player=player['name']))
    game['action_queue'].append(action)

def ensure_action(game, action_name, player):
    """Raise a GamePlayNotAllowedError unless the next action is the given 
    action name and must be performed by the given player.
    
    Returns the first action in the queue if the action and player are at the 
    head of the queue.
    """
    first_action = game['action_queue'][0]
    if first_action['player'] != player['name']:
        raise GamePlayNotAllowedError('need %s to create, not %s' % 
                                      (first_action['player'], player['name']))
    return first_action


#### Playing tiles

def play_tile(game, player, tile):
    """If allowed, play tile from player's rack on to the board. Any new hotels 
    or mergers are taken care of.
    """
    ensure_action(game, 'play_tile', player)
    try:
        player['rack'].remove(tile)
    except ValueError:
        raise GamePlayNotAllowedError('must play tiles from tile rack')
    game['action_queue'].pop(0)
    
    if tile in tiles_that_create_hotels(game):
        append_action(game, 'create_hotel', player, creation_tile=tile)
    else:
        hotel = grows_hotel(game, tile)
        if hotel:
            hotel_named(game, hotel)['tiles'].append(tile)
        else:
            game['lonely_tiles'].append(tile)
        append_action(game, 'play_tile', player)
    player['rack'].append(game['tilebag'].pop())


#### Creating hotels

def create_hotel(game, player, hotel):
    """Create the given hotel at the just-played tile."""
    first_action = ensure_action(game, 'create_hotel', player)
    try:
        creation_tile = first_action['creation_tile']
    except KeyError:
        raise GamePlayNotAllowedError('cannot create tile without playing a '
                                      'creation tile')
    hotel['tiles'] = [creation_tile] + [t for t in adjacent_tiles(creation_tile) 
                                                if t in game['lonely_tiles']]
