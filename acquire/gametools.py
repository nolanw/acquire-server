# Game-manipulating functions. (Games are just dicts so they can be easily 
# passed around and serialized and such.)

from collections import defaultdict
from random import choice, shuffle


hotel_names = 'sackson zeta america fusion hydra quantum phoenix'.split()


class GameError(Exception):
    """Superclass for all exceptions in the gametools module."""
    pass

class GameAlreadyStartedError(GameError):
    pass

class GamePlayNotAllowedError(GameError):
    pass


#### Game creation

def new_game(number=None):
    """Factory for new games. Sets up the basic attributes."""
    game = {'players': [], 'started': False, 'ended': False}
    if number is not None:
        game['number'] = number
    return game


#### Players

def player_named(game, player_name):
    """Find the player with the given name.
    
    Returns:
        - The player dict if the player named is in the game.
        - None if the player named is not in the game.
    """
    return next((p for p in game['players'] if p['name'] == player_name), None)

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
    if game['started'] and not game['ended']:
        raise GameAlreadyStartedError()
    game['players'].remove(player_named(game, player_name))

def host(game):
    """Returns the host player of the given game, or None if no players are in
    the given game."""
    players = game.get('players', [None])
    if players:
        return players[0]
    else:
        return None

def active_player(game):
    """Returns the player who must perform the next action."""
    return player_named(game, game['action_queue'][0]['player'])

def player_after(game, player):
    """Return the player who proceeds the given player in turn order."""
    i = game['players'].index(player) + 1 - len(game['players'])
    return game['players'][i]

def player_order(game, starting_player):
    """Return a generator that yields each player in turn order, beginning with 
    the given starting player.
    """
    cur = starting_player
    while True:
        yield cur
        cur = player_after(game, cur)
        if cur == starting_player:
            raise StopIteration


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
        player['shares'] = dict(zip(hotel_names, [0] * len(hotel_names)))
        player['cash'] = 6000
    
    game['action_queue'] = []
    append_action(game, 'play_tile', starting_player)
    
    game['started'] = True
    for tile in starting_tiles:
        starting_tiles[tile] = starting_tiles[tile]['name']
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
    return next((h['name'] for h in game['hotels'] if tile in h['tiles']), None)

def tiles_that_create_hotels(game):
    """Return a list of tiles that, if played, would cause a new hotel to be 
    created.
    """
    tiles = []
    for on_board in game['lonely_tiles']:
        for adjacent in adjacent_tiles(on_board):
            if adjacent in game['lonely_tiles']:
                continue
            here_they_are = set(where_is_tile(game, t) 
                                for t in adjacent_tiles(adjacent))
            if here_they_are & set(hotel_names):
                continue
            tiles.append(adjacent)
    return tiles

def grows_hotel(game, tile):
    """Returns the hotel that would grow if tile was played, or None if no such 
    hotel exists.
    """
    nearby = set(where_is_tile(game, t) for t in adjacent_tiles(tile))
    return next((h for h in game['hotels'] if h['name'] in nearby), None)

def tiles_that_merge_safe_hotels(game):
    """Return a list of tiles that are unplayable because, if played, they would
    merge a hotel that is safe.
    """
    tiles = defaultdict(int)
    for hotel in game['hotels']:
        if hotel_safe(hotel): 
            for tile in tiles_adjacent_to_hotel(hotel):
                tiles[tile] += 1
    return [t for t, i in tiles.iteritems() if i > 1]

def merge_survivors(game, tile):
    """Returns a list of the possible surviving hotels that would be involved in
    a merger if the given tile was played, or None if the given tile does not 
    merge hotels.
    """
    adjacent_hotels = hotels_adjacent_to_tile(game, tile)
    if len(adjacent_hotels) < 2:
        return None
    elif adjacent_hotels:
        largest = max(map(lambda h: len(h['tiles']), adjacent_hotels))
        return [h for h in adjacent_hotels if len(h['tiles']) == largest]
    else:
        return []


#### Hotels

def hotel_named(game, hotel_name):
    """Find the hotel with the given name.
    
    Returns the dict for the associated hotel, or None if no such hotel.
    """
    return next((h for h in game['hotels'] if h['name'] == hotel_name), None)

def bank_shares(game, hotel):
    """Returns the number of shares in the bank for the given hotel."""
    return 25 - sum(p['shares'].get(hotel['name'], 0) for p in game['players'])

def share_price(hotel):
    """Returns the price per share of hotel."""
    tier = dict(zip(hotel_names, [0, 0, 1, 1, 1, 2, 2]))[hotel['name']]
    size = len(hotel['tiles'])
    if size < 2:
        return 0
    elif size < 6:
        return (size + tier) * 100
    elif size < 11:
        return (6 + tier) * 100
    elif size < 21:
        return (7 + tier) * 100
    elif size < 31:
        return (8 + tier) * 100
    elif size < 41:
        return (9 + tier) * 100
    else:
        return (10 + tier) * 100

def hotel_safe(hotel):
    """Returns True if the given hotel is safe (cannot be merged), or False 
    otherwise.
    """
    return len(hotel['tiles']) > 10

def tiles_adjacent_to_hotel(hotel):
    """Returns the set of tiles that are adjacent to, but not in, the given 
    hotel.
    """
    tiles = set()
    for tile in hotel['tiles']:
        for adjacent in adjacent_tiles(tile):
            if adjacent not in hotel['tiles']:
                tiles.add(adjacent)
    return tiles

def hotels_adjacent_to_tile(game, tile):
    """Returns the list of hotels with a tile adjacent to the given tile."""
    adjacent_hotel_names = set()
    for adjacent in adjacent_tiles(tile):
        location = where_is_tile(game, adjacent)
        if location in hotel_names:
            adjacent_hotel_names.add(location)
    return [hotel_named(game, name) for name in adjacent_hotel_names]

def hotels_off_board(game):
    """Returns the list of hotels that are not on the board in the given game.
    """
    return [h for h in game['hotels'] if not h['tiles']]

def hotels_on_board(game):
    """Returns the list of hotels that are on the board in the given game."""
    return [h for h in game['hotels'] if h['tiles']]


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
        raise GamePlayNotAllowedError('need %s to %s, not %s' % 
                                      (first_action['player'], 
                                       first_action['action'], player['name']))
    elif first_action['action'] != action_name:
        raise GamePlayNotAllowedError('next action is %s, not %s' % 
                                      (first_action['action'], action_name))
    else:
        return first_action


#### Playing tiles

def play_tile(game, player, tile):
    """If allowed, play tile from player's rack on to the board. Any new hotels 
    or mergers are taken care of.
    
    Raises GamePlayNotAllowedError if the given tile cannot be played by the 
    given player.
    """
    ensure_action(game, 'play_tile', player)
    if tile in tiles_that_merge_safe_hotels(game):
        raise GamePlayNotAllowedError('tile %s is unplayable' % tile)
    if not hotels_off_board(game) and tile in tiles_that_create_hotels(game):
        raise GamePlayNotAllowedError('cannot create hotel when all are '
                                      'already on board')
    if tile not in player['rack']:
        raise GamePlayNotAllowedError('must play tiles from tile rack')
    player['rack'].remove(tile)
    game['action_queue'].pop(0)
    
    stock_market_shares = None
    if tile in tiles_that_create_hotels(game):
        append_action(game, 'create_hotel', player, creation_tile=tile)
    else:
        survivors = merge_survivors(game, tile) or []
        survivors = [h['name'] for h in survivors]
        if len(survivors) > 1:
            append_action(game, 'choose_survivor', player, choices=survivors, 
                          tile=tile)
        elif survivors:
            survivor = hotel_named(game, survivors[0])
            stock_market_shares = merge_hotels(game, player, tile, survivor)
            if not game['action_queue']:
                advance_turn(game, player)
        else:
            hotel = grows_hotel(game, tile)
            if hotel:
                hotel['tiles'].append(tile)
                for t in adjacent_tiles(tile):
                    if t in game['lonely_tiles']:
                        hotel['tiles'].append(t)
                        game['lonely_tiles'].remove(t)
            else:
                game['lonely_tiles'].append(tile)
            advance_turn(game, player)
    return stock_market_shares


#### Creating hotels

def create_hotel(game, player, hotel):
    """Create the given hotel at the just-played tile.
    
    Raises GamePlayNotAllowedError if hotel creation is unexpected at this time
    or by the given player.
    """
    first_action = ensure_action(game, 'create_hotel', player)
    if 'creation_tile' not in first_action:
        raise GamePlayNotAllowedError('cannot create tile without playing a '
                                      'creation tile')
    if hotel not in hotels_off_board(game):
        raise GamePlayNotAllowedError('must create hotel that is off the board')
    hotel['tiles'] = [first_action['creation_tile']]
    any_added = True
    while any_added:
        any_added = False
        for tile in tiles_adjacent_to_hotel(hotel):
            if tile in game['lonely_tiles']:
                hotel['tiles'].append(tile)
                game['lonely_tiles'].remove(tile)
                any_added = True
    if bank_shares(game, hotel):
        player['shares'][hotel['name']] += 1
    game['action_queue'].pop(0)
    advance_turn(game, player)


#### Merging hotels

def choose_survivor(game, player, survivor):
    """If the given player was asked to choose a surviving hotel, do so and 
    continue the merge.
    
    Raises GamePlayNotAllowedError if choosing a survivor is unexpected at this 
    time, by the given player, or the survivor is an inappropriate choice.
    """
    first_action = ensure_action(game, 'choose_survivor', player)
    if survivor['name'] not in first_action['choices']:
        raise GamePlayNotAllowedError('survivor must be one of %s, not %s' % 
                                      (first_action['choices'],
                                       survivor['name']))
    game['action_queue'].pop(0)
    return merge_hotels(game, player, first_action['tile'], survivor)

def pay_merge_bonuses(game, hotels):
    """For each hotel in hotels, compute and pay out the majority and minority 
    shareholder bonuses. If there are only two players, the stock market also 
    partakes.
    """
    nearest_hundred_floor = lambda i: i - i % 100
    two_players = len(game['players']) == 2
    stock_market_tiles = {}
    for hotel in hotels:
        shares_held_by = lambda p: p['shares'][hotel['name']]
        shares_held = set(shares_held_by(p) for p in game['players'])
        stock_market = None
        if two_players and game['tilebag']:
            random_tile = choice(game['tilebag'])
            stock_market = int(random_tile[:-1])
            shares_held.add(stock_market)
            stock_market_tiles[hotel['name']] = random_tile
        most_held = max(shares_held)
        if len(shares_held) > 1:
            next_most_held = max(shares_held - set([most_held]))
        else:
            next_most_held = None
        majority_holders = [p for p in game['players']
                                    if shares_held_by(p) == most_held]
        if most_held == stock_market:
            majority_holders.append({'cash': 0})
        minority_holders = [p for p in game['players'] 
                                    if next_most_held and 
                                       shares_held_by(p) == next_most_held]
        if next_most_held and next_most_held == stock_market:
            minority_holders.append({'cash': 0})
        majority_bonus = share_price(hotel) * 10
        minority_bonus = majority_bonus / 2
        if len(majority_holders) > 1:
            bonus = (majority_bonus + minority_bonus) / len(majority_holders)
            majority_bonus = nearest_hundred_floor(bonus)
            minority_bonus = 0
        elif majority_holders:
            if len(minority_holders) > 1:
                bonus = minority_bonus / len(minority_holders)
                minority_bonus = nearest_hundred_floor(bonus)
            elif not minority_holders:
                majority_bonus += minority_bonus
        for p in majority_holders:
            p['cash'] += majority_bonus
        for p in minority_holders:
            p['cash'] += minority_bonus
    return stock_market_tiles

def merge_hotels(game, merging_player, tile, survivor):
    """Merge all hotels adjacent to the given tile into survivor, paying out 
    bonuses as appropriate, then queue actions on the game's action queue for 
    players to handle their shares of disappearing hotels.
    """
    disappearing = [h for h in hotels_adjacent_to_tile(game, tile) 
                            if h != survivor]
    stock_market_tiles = pay_merge_bonuses(game, disappearing)
    disappearing.sort(key=lambda h: -len(h['tiles']))
    for hotel in disappearing:
        for player in player_order(game, merging_player):
            if player['shares'][hotel['name']]:
                append_action(game, 'disburse_shares', player, 
                              hotel=hotel['name'], survivor=survivor['name'])
    game['merge_info'] = {
        'tile': tile, 
        'survivor': survivor['name'],
        'merging_player': merging_player['name'],
    }
    if not game['action_queue']:
        clean_up_merge(game)
    return stock_market_tiles

def disburse_shares(game, player, disbursement):
    """Disburse player's shares in the hotel requested earlier according to 
    disbursement (whose keys can be any subset of {'trade', 'sell'}).
    
    Returns the surviving hotel of the merge that required the shares to be 
    dibursed.
    
    Raises GamePlayNotAllowedError if a share disbursement from the given player 
    was not expected at this time.
    """
    first_action = ensure_action(game, 'disburse_shares', player)
    if first_action['hotel'] != disbursement['hotel']:
        raise GamePlayNotAllowedError('expected disbursement of %s shares, not' 
                                      ' %s shares' % (first_action['hotel'],
                                                      disbursement['hotel']))
    disbursement = dict(disbursement)
    del disbursement['hotel']
    from_hotel = hotel_named(game, game['action_queue'][0]['hotel'])
    shares_held = player['shares'][from_hotel['name']]
    if sum(disbursement.values()) > shares_held:
        raise GamePlayNotAllowedError('cannot disburse more shares than held')
    survivor = hotel_named(game, game['merge_info']['survivor'])
    if 'trade' in disbursement:
        shares_desired = disbursement['trade'] / 2
        if shares_desired > bank_shares(game, survivor):
            raise GamePlayNotAllowedError('not enough shares in the bank')
        player['shares'][from_hotel['name']] -= disbursement['trade']
        player['shares'][survivor['name']] += shares_desired
    if 'sell' in disbursement:
        player['shares'][from_hotel['name']] -= disbursement['sell']
        player['cash'] += disbursement['sell'] * share_price(from_hotel)
    game['action_queue'].pop(0)
    if not game['action_queue']:
        clean_up_merge(game)
    return survivor

def clean_up_merge(game):
    """Put all disappearing hotels' tiles and the merge tile into the surviving 
    hotel, take the disappearing hotels off of the board, then remove the merge
    info and advance the turn.
    """
    survivor = hotel_named(game, game['merge_info']['survivor'])
    merge_tile = game['merge_info']['tile']
    merging_player = player_named(game, game['merge_info']['merging_player'])
    del game['merge_info']
    disappearing = [h for h in hotels_adjacent_to_tile(game, merge_tile) 
                            if h != survivor]
    for hotel in disappearing:
        survivor['tiles'].extend(hotel['tiles'])
        hotel['tiles'] = []
    survivor['tiles'].append(merge_tile)
    for tile in adjacent_tiles(merge_tile):
        if tile in game['lonely_tiles']:
            survivor['tiles'].append(tile)
            game['lonely_tiles'].remove(tile)
    advance_turn(game, merging_player)


#### Buying shares

def purchase(game, player, purchase_order, end_game=False):
    """Purchase the ordered shares on behalf of the given player. If end_game is
    True, attempt to end the game, silently ignoring if that is not allowed.
    
    Raises GamePlayNotAllowedError if purchase is unexpected at this time or by 
    the given player, or if the purchase order breaks any rules:
        - No more than three shares purchased at a time.
        - Must be able to afford all of the ordered shares.
        - Can only purchase shares in a hotel that is on the board.
    """
    ensure_action(game, 'purchase', player)
    if sum(purchase_order.values()) > 3:
        raise GamePlayNotAllowedError('can only purchase at most three shares')
    purchases = {}
    subtotal = 0
    for hotel_name, shares in purchase_order.iteritems():
        hotel = hotel_named(game, hotel_name)
        if hotel and hotel['tiles']:
            if bank_shares(game, hotel) < shares:
                raise GamePlayNotAllowedError('not enough shares of %s in '
                                              'bank' % hotel['name'])
            cost = shares * share_price(hotel)
            purchases[hotel['name']] = shares
            subtotal += cost
    if subtotal > player['cash']:
        raise GamePlayNotAllowedError('cannot afford purchases: %r' % 
                                      purchase_order)
    for hotel_name, shares in purchases.iteritems():
        player['shares'][hotel_name] += shares
    player['cash'] -= subtotal
    game['action_queue'].pop(0)
    if end_game and game_can_end(game):
        return game_over(game)
    else:
        advance_turn(game, player, can_purchase=False)


#### End of turn

def advance_turn(game, player, can_purchase=True):
    """Move the turn along if the action queue is empty, assuming that it is 
    the given player's turn. If can_purchase is True, the given player will be 
    invited to purchase shares if possible. If this is impossible, or if 
    can_purchase is False, the player's rack is replenished and it becomes the 
    next player's turn.
    
    Replenishing a player's rack means drawing tiles from the tilebag until the 
    player's rack has six tiles on it, discarding any permanently unplayable 
    tiles encountered on the rack or in the bag.
    """
    if can_purchase:
        for hotel in game['hotels']:
            if hotel['tiles'] and bank_shares(game, hotel) and \
               player['cash'] > share_price(hotel):
                append_action(game, 'purchase', player)
                return
    for tile in list(player['rack']):
        if tile in tiles_that_merge_safe_hotels(game):
            player['rack'].remove(tile)
    while len(player['rack']) < 6 and game['tilebag']:
        tile = game['tilebag'].pop()
        if tile not in tiles_that_merge_safe_hotels(game):
            player['rack'].append(tile)
    append_action(game, 'play_tile', player_after(game, player))


#### End of game

def game_can_end(game):
    """Return True if the game can end right now, or False otherwise."""
    over_40 = [h for h in game['hotels'] if len(h['tiles']) > 40]
    unsafe_on_board = [h for h in hotels_on_board(game)
                               if h['tiles'] and len(h['tiles']) < 11]
    if over_40 or not unsafe_on_board:
        return True
    else:
        return False

def game_over(game):
    """Attempt to end the game, paying out final bonuses and selling as many 
    shares as possible.
    
    Raises GamePlayNotAllowedError if the game cannot end right now.
    """
    if game['ended']:
        raise GamePlayNotAllowedError('game is already over')
    if not game_can_end(game):
        raise GamePlayNotAllowedError('neither end-game condition met')
    stock_market_shares = {}
    for hotel in hotels_on_board(game):
        stock_market_shares.update(pay_merge_bonuses(game, [hotel]))
        for player in game['players']:
            shares = player['shares']
            name = hotel['name']
            player['cash'] += share_price(hotel) * shares[name]
            shares[name] = 0
    game['ended'] = True
    return stock_market_shares

def winners(game):
    """Return the list of players who won this game."""
    winning_cash = max(map(lambda p: p['cash'], game['players']))
    return [p for p in game['players'] if p['cash'] == winning_cash]
