import unittest

from acquire import gametools

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
    

class TestTilesThatCreateAHotel(unittest.TestCase):
    
    def test_tiles_that_create_hotels(self):
        game = gametools.new_game()
        gametools.set_up_hotels(game)
        game['lonely_tiles'] = ['1A', '8E', '8F', '9I']
        tile_order = lambda t: (int(t[:-1]), t[-1])
        self.assertEqual(sorted(gametools.tiles_that_create_hotels(game), 
                                key=tile_order), 
                         '1B 2A 7E 7F 8D 8G 8I 9E 9F 9H 10I'.split())
    

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
    

class TestTilePlay(ThreePlayerGameTestCase):
    
    @property
    def active_player(self):
        return gametools.player_named(self.game, 
                                      self.game['action_queue'][0]['player'])
    
    def test_legit_play_tile(self):
        player = self.active_player
        tile = player['rack'][0]
        gametools.play_tile(self.game, player, tile)
        self.assertTrue(tile in self.game['lonely_tiles'])
        self.assertTrue(tile not in player['rack'])
    
    def test_play_tile_not_in_rack(self):
        tile = self.game['tilebag'][0]
        with self.assertRaises(gametools.GamePlayNotAllowedError):
            gametools.play_tile(self.game, self.active_player, tile)
        self.assertEqual(self.game['tilebag'][0], tile)
    
    def test_rack_replenishment(self):
        player = self.active_player
        tile = player['rack'][0]
        gametools.play_tile(self.game, self.active_player, tile)
        self.assertEqual(len(player['rack']), 6)
    

if __name__ == '__main__':
    unittest.main()
