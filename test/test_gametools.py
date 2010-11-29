import unittest

from acquire import gametools

def blank_board(game):
    """Remove all tiles from the board."""
    game['lonely_tiles'] = []
    for hotel in game['hotels']:
        hotel['tiles'] = []

class TestAddingAndRemovingPlayers(unittest.TestCase):
    
    def setUp(self):
        self.game = gametools.new_game()
    
    def test_add_player_to_unstarted_game(self):
        gametools.add_player_named(self.game, 'testmanican')
        self.assertEqual(len(self.game['players']), 1, self.game)
        gametools.add_player_named(self.game, 'testvetica')
        self.assertEqual(len(self.game['players']), 2, self.game)
    
    def test_remove_player_from_unstarted_game(self):
        gametools.add_player_named(self.game, 'testmanican')
        gametools.add_player_named(self.game, 'testvetica')
        gametools.remove_player_named(self.game, 'testmanican')
        self.assertEqual(len(self.game['players']), 1, self.game)
        self.assertEqual(self.game['players'][0]['name'], 'testvetica')
    
    def test_add_player_to_started_game(self):
        gametools.add_player_named(self.game, 'chumpwoman')
        gametools.start_game(self.game)
        with self.assertRaises(gametools.GameAlreadyStartedError):
            gametools.add_player_named(self.game, 'chumpman')
    
    def test_remove_player_from_started_game(self):
        gametools.add_player_named(self.game, 'testwomanican')
        gametools.start_game(self.game)
        with self.assertRaises(gametools.GameAlreadyStartedError):
            gametools.remove_player_named(self.game, 'testwomanican')
    
    def test_remove_player_from_finished_game(self):
        gametools.add_player_named(self.game, 'testwomanican')
        gametools.start_game(self.game)
        self.game['ended'] = True
        gametools.remove_player_named(self.game, 'testwomanican')
        self.assertFalse(self.game['players'])
    

class TestAdjacentTiles(unittest.TestCase):
    
    def test_adjacent_tiles_middle(self):
        tile = '5D'
        adjacent = gametools.adjacent_tiles(tile)
        self.assertEqual(sorted(adjacent), ['4D', '5C', '5E', '6D'])
    
    def test_adjacent_tiles_edge(self):
        tile = '7A'
        adjacent = gametools.adjacent_tiles(tile)
        self.assertEqual(sorted(adjacent), ['6A', '7B', '8A'])
    
    def test_adjacent_tiles_corner(self):
        tile = '12I'
        adjacent = gametools.adjacent_tiles(tile)
        self.assertEqual(sorted(adjacent), ['11I', '12H'])
    

class TestWhereIsTile(unittest.TestCase):
    
    def test_where_is_tile(self):
        game = gametools.new_game()
        gametools.set_up_hotels(game)
        game['lonely_tiles'] = ['4C']
        quantum = gametools.hotel_named(game, 'quantum')
        quantum['tiles'] = ['8D', '9D']
        self.assertEqual(gametools.where_is_tile(game, '1A'), None)
        self.assertEqual(gametools.where_is_tile(game, '4C'), 'lonely')
        self.assertEqual(gametools.where_is_tile(game, '4D'), None)
        self.assertEqual(gametools.where_is_tile(game, '8D'), 'quantum')
    

tile_order = lambda t: (int(t[:-1]), t[-1])

class TestTilesThatCreateAHotel(unittest.TestCase):
    
    def setUp(self):
        self.game = gametools.new_game()
        gametools.set_up_hotels(self.game)
    
    def test_tiles_that_create_hotels(self):
        self.game['lonely_tiles'] = ['1A', '8E', '8F', '9I']
        self.assertEqual(sorted(gametools.tiles_that_create_hotels(self.game), 
                                key=tile_order), 
                         '1B 2A 7E 7F 8D 8G 8I 9E 9F 9H 10I'.split())
    
    def test_tiny_board(self):
        self.game['lonely_tiles'] = ['1A']
        self.assertEqual(sorted(gametools.tiles_that_create_hotels(self.game), 
                                key=tile_order), 
                         ['1B', '2A'])
    
    def test_tile_adjacent_to_lonely_tile_and_hotel(self):
        self.game['lonely_tiles'] = ['1A']
        gametools.hotel_named(self.game, 'sackson')['tiles'] = ['1C', '1D']
        self.assertFalse('1B' in gametools.tiles_that_create_hotels(self.game))
    

class TestGrowsHotel(unittest.TestCase):
    
    def test_grows_hotel(self):
        game = gametools.new_game()
        gametools.add_player_named(game, 'champ')
        gametools.start_game(game)
        blank_board(game)
        hydra = gametools.hotel_named(game, 'hydra')
        hydra['tiles'] = ['6A', '6B', '7B']
        for tile in ['5A']:
            self.assertTrue(gametools.grows_hotel(game, tile), tile)
        for tile in ['1C', '5C', '8E']:
            self.assertFalse(gametools.grows_hotel(game, tile), tile)
    

class TestSharePrice(unittest.TestCase):
    
    def embiggen_and_check_prices(self, hotel, steps, prices):
        for step, price in zip(steps, prices):
            hotel['tiles'].extend([0] * step)
            self.assertEqual(gametools.share_price(hotel), price)
    
    def test_tier_0(self):
        zeta = {'name': 'zeta', 'tiles': []}
        embiggen = [0, 2, 2, 3, 14]
        expected = [0, 200, 400, 600, 800]
        self.embiggen_and_check_prices(zeta, embiggen, expected)
    
    def test_tier_1(self):
        hydra = {'name': 'hydra', 'tiles': []}
        embiggen = [0, 2, 2, 3, 14]
        expected = [0, 300, 500, 700, 900]
        self.embiggen_and_check_prices(hydra, embiggen, expected)
    

class ThreePlayerGameTestCase(unittest.TestCase):
    
    def setUp(self):
        self.game = gametools.new_game()
        gametools.add_player_named(self.game, 'testwomanican')
        gametools.add_player_named(self.game, 'testmanican')
        gametools.add_player_named(self.game, 'testvetica')
        self.starting_tiles = gametools.start_game(self.game)
        self.player = gametools.active_player(self.game)
        for hotel in self.game['hotels']:
            setattr(self, hotel['name'], hotel)
    
    def remember_cash(self):
        self.cash_before = map(lambda p: p['cash'], self.game['players'])
    
    def cash_difference(self):
        cash_after = map(lambda p: p['cash'], self.game['players'])
        return [a - b for b, a in zip(self.cash_before, cash_after)]
    

class TestGameSetup(ThreePlayerGameTestCase):
    
    def test_starting_player_tile_draw(self):
        self.assertEqual(len(self.starting_tiles), len(self.game['players']))
        tileorder = lambda t: t[-1] + t[:-1]
        starting_tile = sorted(self.starting_tiles.keys(), key=tileorder)[0]
        self.assertEqual(self.game['players'][0]['name'], 
                         self.starting_tiles[starting_tile])
    
    def test_tile_racks(self):
        for player in self.game['players']:
            self.assertEqual(len(player['rack']), 6)
    
    def test_tilebag(self):
        tilebag_should_be = sorted([str(i) + a for i in range(1, 13) 
                                               for a in 'ABCDEFGHI'])
        for player in self.game['players']:
            for tile in player['rack']:
                tilebag_should_be.remove(tile)
        for tile in self.game['lonely_tiles']:
            tilebag_should_be.remove(tile)
        self.assertEqual(tilebag_should_be, sorted(self.game['tilebag']))
    
    def test_hotels(self):
        names = 'sackson zeta america fusion hydra quantum phoenix'.split()
        for name in names:
            hotel = gametools.hotel_named(self.game, name)
            self.assertTrue(hotel)
            self.assertEqual(len(hotel['tiles']), 0)
            self.assertEqual(gametools.bank_shares(self.game, hotel), 25)
    
    def test_starting_player(self):
        first_action = self.game['action_queue'][0]
        self.assertEqual(first_action['player'], 
                         self.game['players'][0]['name'])
        self.assertEqual(first_action['action'], 'play_tile')
    
    def test_active_player(self):
        self.assertEqual(self.game['players'][0], self.player)
    

class TestTilePlay(ThreePlayerGameTestCase):
    
    def test_legit_play_tile(self):
        tile = None
        for rack_tile in self.player['rack']:
            if rack_tile not in gametools.tiles_that_create_hotels(self.game):
                tile = rack_tile
                break
        gametools.play_tile(self.game, self.player, tile)
        self.assertTrue(tile in self.game['lonely_tiles'])
        self.assertTrue(tile not in self.player['rack'])
    
    def test_play_tile_not_in_rack(self):
        tile = self.game['tilebag'][0]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, self.player, tile)
        self.assertEqual(self.game['tilebag'][0], tile)
    
    def test_other_player_play_tile(self):
        other_player = self.game['players'][1]
        tile = other_player['rack'][0]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, other_player, tile)
    
    def test_rack_replenishment(self):
        blank_board(self.game)
        tile = self.player['rack'][0]
        gametools.play_tile(self.game, self.player, tile)
        self.assertEqual(len(self.player['rack']), 6)
    
    def test_nonexistent_tile_play(self):
        nonexistent_tiles = ['0E', '11', '1J', '13C']
        for tile in nonexistent_tiles:
            with self.assertRaises(gametools.GamePlayNotAllowedError):
                gametools.play_tile(self.game, self.player, tile)
    
    def test_playing_safe_hotel_merge_tile(self):
        self.quantum['tiles'] = [str(i) + 'A' for i in xrange(1, 13)]
        self.phoenix['tiles'] = [str(i) + 'C' for i in xrange(1, 13)]
        tile = self.player['rack'][0] = '4B'
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, self.player, tile)
    
    def test_playing_creation_tile_when_no_available_hotels(self):
        blank_board(self.game)
        tilesets = [['1A', '2A'], ['4A', '5A'], ['7A', '8A'], ['10A', '11A'], 
                    ['1C', '2C'], ['4C', '5C'], ['7C', '8C']]
        for hotel, tileset in zip(self.game['hotels'], tilesets):
            hotel['tiles'] = tileset
        self.game['lonely_tiles'] = ['1I']
        tile = self.player['rack'][0] = '2I'
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, self.player, tile)
    

class TestHotelCreation(ThreePlayerGameTestCase):
    
    def force_active_player_to_create_hotel(self):
        tile_to_play = gametools.tiles_that_create_hotels(self.game)[0]
        player = gametools.active_player(self.game)
        player['rack'][0] = tile_to_play
        gametools.play_tile(self.game, player, tile_to_play)
    
    def test_create_hotel(self):
        self.force_active_player_to_create_hotel()
        gametools.create_hotel(self.game, self.player, self.sackson)
        self.assertTrue(self.sackson['tiles'])
    
    def test_wrong_player_create_hotel(self):
        self.force_active_player_to_create_hotel()
        other_player = self.game['players'][1]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.create_hotel(self.game, other_player, self.fusion)
    
    def test_create_hotel_without_playing_tile(self):
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.create_hotel(self.game, self.player, self.zeta)
    
    def test_create_hotel_already_on_board(self):
        self.force_active_player_to_create_hotel()
        gametools.create_hotel(self.game, self.player, self.hydra)
        gametools.purchase(self.game, self.player, {})
        self.force_active_player_to_create_hotel()
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.create_hotel(self.game, self.player, self.hydra)
    
    def test_tiles_no_longer_lonely(self):
        self.force_active_player_to_create_hotel()
        gametools.create_hotel(self.game, self.player, self.quantum)
        for tile in self.quantum['tiles']:
            self.assertTrue(tile not in self.game['lonely_tiles'])
    
    def test_tiles_included_two_adjacencies_away(self):
        blank_board(self.game)
        self.game['lonely_tiles'] = ['1A', '2A']
        tile = self.player['rack'][0] = '1B'
        gametools.play_tile(self.game, self.player, tile)
        gametools.create_hotel(self.game, self.player, self.zeta)
        self.assertTrue('2A' in self.zeta['tiles'])
    
    def test_founders_share(self):
        self.force_active_player_to_create_hotel()
        gametools.create_hotel(self.game, self.player, self.sackson)
        self.assertEqual(self.player['shares']['sackson'], 1)
    
    def test_no_founders_share_when_none_available(self):
        self.force_active_player_to_create_hotel()
        other_player = self.game['players'][1]
        other_player['shares']['america'] = 25
        gametools.create_hotel(self.game, self.player, self.america)
        self.assertEqual(self.player['shares']['america'], 0)
    

class TestHotelGrowth(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestHotelGrowth, self).setUp()
        blank_board(self.game)
        self.phoenix['tiles'] = ['1C', '2C']
    
    def test_one_tile_added_to_hotel(self):
        tile = self.player['rack'][0] = '2D'
        gametools.play_tile(self.game, self.player, tile)
        self.assertEqual(len(self.phoenix['tiles']), 3)
        self.assertEqual(gametools.where_is_tile(self.game, tile), 'phoenix')
    
    def test_many_tiles_added_to_hotel(self):
        for tile in ['2D', '1B', '1A', '2A']:
            player = gametools.active_player(self.game)
            player['rack'][0] = tile
            gametools.play_tile(self.game, player, tile)
            gametools.purchase(self.game, player, {})
            self.assertEqual(gametools.where_is_tile(self.game, tile), 
                             'phoenix')
        self.assertEqual(len(self.phoenix['tiles']), 6)
    
    def test_adjacent_lonely_tiles_added_to_hotel(self):
        self.game['lonely_tiles'] = ['4C']
        tile = self.player['rack'][0] = '3C'
        gametools.play_tile(self.game, self.player, tile)
        self.assertTrue('4C' in self.phoenix['tiles'])
        self.assertTrue('4C' not in self.game['lonely_tiles'])
    

class TestTurnRotation(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestTurnRotation, self).setUp()
        blank_board(self.game)
    
    def test_player_after(self):
        player = gametools.player_after(self.game, self.player)
        self.assertEqual(player, self.game['players'][1])
        player = gametools.player_after(self.game, player)
        self.assertEqual(player, self.game['players'][2])
        player = gametools.player_after(self.game, player)
        self.assertEqual(player, self.game['players'][0])
    
    def test_turn_rotates_after_playing_tile(self):
        gametools.play_tile(self.game, self.player, self.player['rack'][0])
        self.assertEqual(gametools.active_player(self.game), 
                         gametools.player_after(self.game, self.player))
    
    def test_turn_rotates_after_creating_hotel(self):
        self.game['lonely_tiles'] = ['1A']
        tile = self.player['rack'][0] = '1B'
        gametools.play_tile(self.game, self.player, tile)
        gametools.create_hotel(self.game, self.player, self.zeta)
        gametools.purchase(self.game, self.player, {})
        self.assertEqual(gametools.active_player(self.game), 
                         self.game['players'][1])
    
    def test_tile_rack_replenished_at_end_of_turn(self):
        self.game['lonely_tiles'] = ['9D']
        tile = self.player['rack'][0] = '8D'
        gametools.play_tile(self.game, self.player, tile)
        self.assertEqual(len(self.player['rack']), 5)
    

class TestPurchasingShares(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestPurchasingShares, self).setUp()
        blank_board(self.game)
    
    def make_purchase_the_next_action(self):
        self.game['action_queue'][0]['action'] = 'purchase'
    
    def test_offer_purchase_after_hotel_creation(self):
        self.game['lonely_tiles'] = ['7C']
        tile = self.player['rack'][0] = '8C'
        gametools.play_tile(self.game, self.player, tile)
        gametools.create_hotel(self.game, self.player, self.quantum)
        first_action = self.game['action_queue'][0]
        self.assertEqual(first_action['action'], 'purchase')
        self.assertEqual(first_action['player'], self.player['name'])
    
    def test_purchase_shares_in_one_hotel(self):
        self.zeta['tiles'] = ['9C', '9D']
        self.make_purchase_the_next_action()
        self.assertEqual(self.player['shares']['zeta'], 0)
        gametools.purchase(self.game, self.player, {'zeta': 3})
        self.assertEqual(self.player['shares']['zeta'], 3)
        self.assertEqual(self.player['cash'], 5400)
    
    def test_do_not_offer_purchase_when_no_hotels_on_board(self):
        gametools.play_tile(self.game, self.player, self.player['rack'][0])
        self.assertNotEqual(self.game['action_queue'][0]['action'], 'purchase')
    
    def test_do_not_offer_purchase_when_no_shares_affordable(self):
        self.fusion['tiles'] = ['8H', '9H']
        self.player['cash'] = 200
        gametools.play_tile(self.game, self.player, self.player['rack'][0])
        self.assertNotEqual(self.game['action_queue'][0]['action'], 'purchase')
    
    def test_do_not_offer_purchase_when_no_shares_in_bank(self):
        self.hydra['tiles'] = ['2I', '3I']
        self.game['players'][1]['shares']['hydra'] = 25
        gametools.play_tile(self.game, self.player, self.player['rack'][0])
        self.assertNotEqual(self.game['action_queue'][0]['action'], 'purchase')
    
    def test_purchase_too_many_shares(self):
        self.make_purchase_the_next_action()
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.purchase(self.game, self.player, {'sackson': 4})
    
    def test_purchase_shares_in_off_board_hotels(self):
        self.america['tiles'] = ['3E', '3D', '4D', '4C']
        self.make_purchase_the_next_action()
        gametools.purchase(self.game, self.player, {'fusion': 1})
        self.assertEqual(self.player['shares']['fusion'], 0)
    
    def test_unaffordable_purchase(self):
        self.sackson['tiles'] = ['11A', '11C', '12A', '12B', '12C']
        self.zeta['tiles'] = ['12H', '12I']
        self.player['cash'] = 200
        self.make_purchase_the_next_action()
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.purchase(self.game, self.player, {'sackson': 3})
    
    def test_purchase_shares_in_nonexistant_hotel(self):
        self.phoenix['tiles'] = ['8G', '8H', '8I']
        self.make_purchase_the_next_action()
        gametools.purchase(self.game, self.player, {'febtober': 2})
        self.assertTrue('febtober' not in self.player['shares'])
    
    def test_purchase_more_shares_than_in_bank(self):
        self.quantum['tiles'] = ['1A', '2A']
        self.game['players'][1]['shares']['quantum'] = 24
        self.make_purchase_the_next_action()
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.purchase(self.game, self.player, {'quantum': 2})
    

class TestMerge(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestMerge, self).setUp()
        blank_board(self.game)
        self.quantum['tiles'] = ['5H', '5I']
        self.fusion['tiles'] = ['3H', '3I']
        self.other_player, self.third_player = self.game['players'][1:3]
        self.tile = self.player['rack'][0] = '4H'
    
    def merge_quantum_and_fusion(self, survivor=None):
        gametools.play_tile(self.game, self.player, self.tile)
        if survivor:
            gametools.choose_survivor(self.game, self.player, survivor)
    
    def merge_quantum_fusion_and_phoenix(self):
        self.phoenix['tiles'] = ['4G', '4F', '4E', '4D']
        self.merge_quantum_and_fusion()
    
    def test_choose_merge_survivor(self):
        self.merge_quantum_and_fusion(self.quantum)
    
    def test_choose_merge_survivor_when_no_choice(self):
        self.quantum['tiles'].append('5G')
        self.merge_quantum_and_fusion()
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.choose_survivor(self.game, self.player, self.fusion)
    
    def test_choose_inappropriate_merge_survivor(self):
        self.merge_quantum_and_fusion()
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.choose_survivor(self.game, self.player, self.sackson)
    
    def test_single_shareholder_bonus_tier2(self):
        self.player['shares']['quantum'] = 1
        self.remember_cash()
        self.merge_quantum_and_fusion(self.fusion)
        self.assertEqual(self.cash_difference(), [6000, 0, 0])
    
    def test_majority_minority_shareholder_bonus_tier2(self):
        self.player['shares']['quantum'] = 2
        self.other_player['shares']['quantum'] = 1
        self.remember_cash()
        self.merge_quantum_and_fusion(self.fusion)
        self.assertEqual(self.cash_difference(), [4000, 2000, 0])
    
    def test_tied_majority_shareholder_bonus_tier2(self):
        self.player['shares']['quantum'] = 2
        self.other_player['shares']['quantum'] = 2
        self.third_player['shares']['quantum'] = 1
        self.remember_cash()
        self.merge_quantum_and_fusion(self.fusion)
        self.assertEqual(self.cash_difference(), [3000, 3000, 0])
    
    def test_tied_minority_shareholder_bonus_tier2(self):
        self.player['shares']['quantum'] = 2
        self.other_player['shares']['quantum'] = 1
        self.third_player['shares']['quantum'] = 1
        self.remember_cash()
        self.merge_quantum_and_fusion(self.fusion)
        self.assertEqual(self.cash_difference(), [4000, 1000, 1000])
    
    def test_disburse_shares_after_merge(self):
        self.player['shares']['quantum'] = 2
        self.merge_quantum_and_fusion(self.fusion)
        gametools.disburse_shares(self.game, self.player, {'hotel': 'quantum'})
    
    def test_inappropriate_share_disbursement(self):
        self.player['shares']['fusion'] = 1
        self.merge_quantum_and_fusion(self.fusion)
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.player, {})
    
    def test_out_of_turn_share_disbursement(self):
        self.player['shares']['quantum'] = 1
        self.other_player['shares']['quantum'] = 1
        self.merge_quantum_and_fusion(self.fusion)
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.other_player, 
                                      {'hotel': 'quantum'})
    
    def test_trade_shares(self):
        self.player['shares']['quantum'] = 2
        self.merge_quantum_and_fusion(self.fusion)
        disbursement = {'trade': 2, 'hotel': 'quantum'}
        gametools.disburse_shares(self.game, self.player, disbursement)
        self.assertEqual(self.player['shares']['fusion'], 1)
    
    def test_trade_more_shares_than_held(self):
        self.player['shares']['quantum'] = 2
        self.merge_quantum_and_fusion(self.fusion)
        disbursement = {'trade': 4, 'hotel': 'quantum'}
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.player, disbursement)
    
    def test_trade_for_more_shares_than_available(self):
        self.player['shares']['quantum'] = 10
        self.other_player['shares']['fusion'] = 22
        self.merge_quantum_and_fusion(self.fusion)
        disbursement = {'trade': 10, 'hotel': 'quantum'}
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.player, disbursement)
    
    def test_sell_shares(self):
        self.player['shares']['quantum'] = 1
        self.merge_quantum_and_fusion(self.fusion)
        self.remember_cash()
        disbursement = {'sell': 1, 'hotel': 'quantum'}
        gametools.disburse_shares(self.game, self.player, disbursement)
        self.assertEqual(self.cash_difference(), [400, 0, 0])
    
    def test_sell_more_shares_than_held(self):
        self.player['shares']['quantum'] = 1
        self.merge_quantum_and_fusion(self.fusion)
        disbursement = {'sell': 2, 'hotel': 'quantum'}
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.player, disbursement)
    
    def test_purchase_shares_after_merge(self):
        self.player['shares']['quantum'] = 1
        self.merge_quantum_and_fusion(self.fusion)
        gametools.disburse_shares(self.game, self.player, {'hotel': 'quantum'})
        first_action = self.game['action_queue'][0]
        self.assertEqual(first_action['action'], 'purchase')
        self.assertEqual(first_action['player'], self.player['name'])
    
    def test_surviving_hotel_gains_appropriate_tiles(self):
        self.merge_quantum_and_fusion(self.fusion)
        tiles = ['3H', '3I', '4H', '5H', '5I']
        self.assertEqual(sorted(self.fusion['tiles']), tiles)
        self.assertTrue('4H' not in self.game['lonely_tiles'])
    
    def test_three_way_merge(self):
        self.merge_quantum_fusion_and_phoenix()
        tiles = ['3H', '3I', '4D', '4E', '4F', '4G', '4H', '5H', '5I']
        self.assertEqual(sorted(self.phoenix['tiles']), tiles)
    
    def test_multiple_disappearing_hotels_disbursement_order1(self):
        self.quantum['tiles'].append('6H')
        self.player['shares']['quantum'] = 1
        self.player['shares']['fusion'] = 1
        self.merge_quantum_fusion_and_phoenix()
        disbursement = {'sell': 1, 'hotel': 'fusion'}
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.player, disbursement)
    
    def test_multiple_disappearing_hotels_disbursement_order2(self):
        self.fusion['tiles'].append('2H')
        self.player['shares']['quantum'] = 1
        self.player['shares']['fusion'] = 1
        self.merge_quantum_fusion_and_phoenix()
        disbursement = {'sell': 1, 'hotel': 'quantum'}
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.disburse_shares(self.game, self.player, disbursement)
    
    def test_lonely_tiles_adjacent_to_merge_tile(self):
        self.game['lonely_tiles'] = ['4I']
        self.merge_quantum_and_fusion(self.quantum)
        self.assertTrue('4I' in self.quantum['tiles'])
        self.assertTrue('4I' not in self.game['lonely_tiles'])
    

class TestUnplayableTileReplenishment(ThreePlayerGameTestCase):
    
    def test_discard_and_replenish_unplayable_rack_tiles(self):
        blank_board(self.game)
        self.zeta['tiles'] = [str(i) + 'A' for i in xrange(1, 13)]
        self.america['tiles'] = [str(i) + 'C' for i in xrange(1, 13)]
        unplayable = [str(i) + 'B' for i in xrange(1, 6)]
        self.player['rack'][1:6] = unplayable
        for tile in unplayable:
            if tile in self.game['tilebag']:
                self.game['tilebag'].remove(tile)
        tile = self.player['rack'][0] = '10D'
        gametools.play_tile(self.game, self.player, tile)
        gametools.purchase(self.game, self.player, {})
        for tile in unplayable:
            self.assertTrue(tile not in self.player['rack'])
        self.assertEqual(len(self.player['rack']), 6)
    

class TestEndOfGame(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestEndOfGame, self).setUp()
        blank_board(self.game)
    
    def test_inappropriate_game_end(self):
        self.sackson['tiles'] = ['1A', '2A']
        gametools.play_tile(self.game, self.player, self.player['rack'][0])
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.purchase(self.game, self.player, {}, end_game=True)
    
    def test_appropriate_game_end(self):
        self.sackson['tiles'] = [str(i) + 'A' for i in xrange(1, 13)]
        tile = self.player['rack'][0] = '1D'
        gametools.play_tile(self.game, self.player, tile)
        gametools.purchase(self.game, self.player, {}, end_game=True)
        self.assertTrue(self.game['ended'])
    
    def test_bonuses_awarded_at_game_end(self):
        self.sackson['tiles'] = [str(i) + 'A' for i in xrange(1, 13)]
        self.player['shares']['sackson'] = 1
        tile = self.player['rack'][0] = '1D'
        self.remember_cash()
        gametools.play_tile(self.game, self.player, tile)
        gametools.purchase(self.game, self.player, {}, end_game=True)
        self.assertEqual(self.cash_difference(), [11200, 0, 0])
    

if __name__ == '__main__':
    unittest.main()
