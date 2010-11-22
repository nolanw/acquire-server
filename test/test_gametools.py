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
    

class TestGrowsHotel(unittest.TestCase):
    
    def test_grows_hotel(self):
        game = gametools.new_game()
        gametools.add_player_named(game, 'champ')
        gametools.start_game(game)
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
    

class TestGameSetup(ThreePlayerGameTestCase):
    
    def test_starting_player_tile_draw(self):
        self.assertEqual(len(self.starting_tiles), len(self.game['players']))
        tileorder = lambda t: t[-1] + t[:-1]
        starting_tile = sorted(self.starting_tiles.keys(), key=tileorder)[0]
        self.assertEqual(self.game['players'][0], 
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
        first_player = self.game['players'][0]
        self.assertEqual(first_player, gametools.active_player(self.game))
    

class TestTilePlay(ThreePlayerGameTestCase):
    
    def test_legit_play_tile(self):
        player = gametools.active_player(self.game)
        tile = None
        for rack_tile in player['rack']:
            if rack_tile not in gametools.tiles_that_create_hotels(self.game):
                tile = rack_tile
                break
        gametools.play_tile(self.game, player, tile)
        self.assertTrue(tile in self.game['lonely_tiles'])
        self.assertTrue(tile not in player['rack'])
    
    def test_play_tile_not_in_rack(self):
        tile = self.game['tilebag'][0]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, gametools.active_player(self.game), 
                                tile)
        self.assertEqual(self.game['tilebag'][0], tile)
    
    def test_other_player_play_tile(self):
        other_player = self.game['players'][1]
        tile = other_player['rack'][0]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, other_player, tile)
    
    def test_rack_replenishment(self):
        player = gametools.active_player(self.game)
        tile = player['rack'][0]
        gametools.play_tile(self.game, player, tile)
        self.assertEqual(len(player['rack']), 6)
    

class TestHotelCreation(ThreePlayerGameTestCase):
    
    def force_active_player_to_create_hotel(self):
        tile_to_play = gametools.tiles_that_create_hotels(self.game)[0]
        player = gametools.active_player(self.game)
        player['rack'][0] = tile_to_play
        gametools.play_tile(self.game, player, tile_to_play)
    
    def test_create_hotel(self):
        self.force_active_player_to_create_hotel()
        sackson = gametools.hotel_named(self.game, 'sackson')
        gametools.create_hotel(self.game, gametools.active_player(self.game), 
                               sackson)
        self.assertTrue(sackson['tiles'])
    
    def test_wrong_player_create_hotel(self):
        self.force_active_player_to_create_hotel()
        fusion = gametools.hotel_named(self.game, 'fusion')
        other_player = self.game['players'][1]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.create_hotel(self.game, other_player, fusion)
    
    def test_create_hotel_without_playing_tile(self):
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.create_hotel(self.game, 
                                   gametools.active_player(self.game), 
                                   'zeta')
    

class TestHotelGrowth(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestHotelGrowth, self).setUp()
        blank_board(self.game)
        self.phoenix = gametools.hotel_named(self.game, 'phoenix')
        self.phoenix['tiles'] = ['1C', '2C']
    
    def test_one_tile_added_to_hotel(self):
        player = self.game['players'][0]
        tile = '2D'
        player['rack'][0] = tile
        gametools.play_tile(self.game, player, tile)
        self.assertEqual(len(self.phoenix['tiles']), 3)
        self.assertEqual(gametools.where_is_tile(self.game, tile), 'phoenix', 
                         tile)
    
    def test_many_tiles_added_to_hotel(self):
        for tile in ['2D', '1B', '1A', '2A']:
            player = gametools.active_player(self.game)
            player['rack'][0] = tile
            gametools.play_tile(self.game, player, tile)
            self.assertEqual(gametools.where_is_tile(self.game, tile), 
                             'phoenix', tile)
        self.assertEqual(len(self.phoenix['tiles']), 6)
    

class TestTurnRotation(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestTurnRotation, self).setUp()
        blank_board(self.game)
    
    def test_player_after(self):
        player = gametools.active_player(self.game)
        player = gametools.player_after(self.game, player)
        self.assertEqual(player, self.game['players'][1])
        player = gametools.player_after(self.game, player)
        self.assertEqual(player, self.game['players'][2])
        player = gametools.player_after(self.game, player)
        self.assertEqual(player, self.game['players'][0])
    
    def test_turn_rotates_after_playing_tile(self):
        player = gametools.active_player(self.game)
        gametools.play_tile(self.game, player, player['rack'][0])
        self.assertEqual(gametools.active_player(self.game), 
                         gametools.player_after(self.game, player))
    
    def test_turn_rotates_after_creating_hotel(self):
        self.game['lonely_tiles'] = ['1A']
        player = gametools.active_player(self.game)
        tile = '1B'
        player['rack'][0] = tile
        gametools.play_tile(self.game, player, tile)
        hotel = gametools.hotel_named(self.game, 'zeta')
        gametools.create_hotel(self.game, player, hotel)
        gametools.purchase(self.game, player, {})
        self.assertEqual(gametools.active_player(self.game), 
                         self.game['players'][1])
    

class TestPurchasingShares(ThreePlayerGameTestCase):
    
    def setUp(self):
        super(TestPurchasingShares, self).setUp()
        blank_board(self.game)
    
    def test_offer_purchase_after_hotel_creation(self):
        self.game['lonely_tiles'] = ['7C']
        player = gametools.active_player(self.game)
        tile = player['rack'][0] = '8C'
        gametools.play_tile(self.game, player, tile)
        quantum = gametools.hotel_named(self.game, 'quantum')
        gametools.create_hotel(self.game, player, quantum)
        first_action = self.game['action_queue'][0]
        self.assertEqual(first_action['action'], 'purchase')
        self.assertEqual(first_action['player'], player['name'])
    
    def test_purchase_shares_in_one_hotel(self):
        player = gametools.active_player(self.game)
        zeta = gametools.hotel_named(self.game, 'zeta')
        zeta['tiles'] = ['9C', '9D']
        for tile in zeta['tiles']:
            if tile in self.game['lonely_tiles']:
                self.game['lonely_tiles'].remove(tile)
        self.game['action_queue'][0]['action'] = 'purchase'
        self.assertEqual(player['shares']['zeta'], 0)
        gametools.purchase(self.game, player, {'zeta': 3})
        self.assertEqual(player['shares']['zeta'], 3)
        self.assertEqual(player['cash'], 5400)
    
    def test_do_not_offer_purchase_when_no_hotels_on_board(self):
        player = gametools.active_player(self.game)
        gametools.play_tile(self.game, player, player['rack'][0])
        self.assertNotEqual(self.game['action_queue'][0]['action'], 'purchase')
    
    def test_purchase_too_many_shares(self):
        player = gametools.active_player(self.game)
        self.game['action_queue'][0]['action'] = 'purchase'
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.purchase(self.game, player, {'sackson': 4})
    

if __name__ == '__main__':
    unittest.main()
