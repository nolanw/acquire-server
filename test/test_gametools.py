import unittest

from acquire import gametools

class TestAddingAndRemovingPlayers(unittest.TestCase):
    
    def setUp(self):
        self.game = gametools.new_game()
    
    def test_add_player_to_unstarted_game(self):
        gametools.add_player_named(self.game, 'testmanican')
        self.assertTrue(len(self.game['players']) == 1, self.game)
        gametools.add_player_named(self.game, 'testvetica')
        self.assertTrue(len(self.game['players']) == 2, self.game)
    
    def test_remove_player_from_unstarted_game(self):
        gametools.add_player_named(self.game, 'testmanican')
        gametools.add_player_named(self.game, 'testvetica')
        gametools.remove_player_named(self.game, 'testmanican')
        self.assertTrue(len(self.game['players']) == 1, self.game)
        self.assertTrue(self.game['players'][0]['name'] == 'testvetica')
    
    def test_add_player_to_started_game(self):
        gametools.start_game(self.game)
        with self.assertRaises(gametools.GameAlreadyStartedError):
            gametools.add_player_named(self.game, 'chumpman')
    
    def test_remove_player_from_started_game(self):
        gametools.add_player_named(self.game, 'testwomanican')
        gametools.start_game(self.game)
        with self.assertRaises(gametools.GameAlreadyStartedError):
            gametools.remove_player_named(self.game, 'testwomanican')
    

class TestGameSetup(unittest.TestCase):
    
    def setUp(self):
        self.game = gametools.new_game()
        gametools.add_player_named(self.game, 'testwomanican')
        gametools.add_player_named(self.game, 'testmanican')
        gametools.add_player_named(self.game, 'testvetica')
        self.starting_tiles = gametools.start_game(self.game)
    
    def test_starting_player_tile_draw(self):
        self.assertEqual(len(self.starting_tiles), len(self.game['players']))
        tileorder = lambda t: t[-1] + t[:-1]
        starting_tile = sorted(self.starting_tiles.keys(), key=tileorder)[0]
        self.assertEqual(self.game['players'][0], 
                         self.starting_tiles[starting_tile])
    
    def test_tile_racks(self):
        for player in self.game['players']:
            self.assertTrue(len(player['rack']) == 6)
    
    def test_tilebag(self):
        tilebag_should_be = sorted([str(i) + a for i in range(1, 13) 
                                               for a in 'ABCDEFGHI'])
        for player in self.game['players']:
            for tile in player['rack']:
                tilebag_should_be.remove(tile)
        self.assertTrue(tilebag_should_be == sorted(self.game['tilebag']))
        for tile in self.game['lonely_tiles']:
            tilebag_should_be.remove(tile)
    

if __name__ == '__main__':
    unittest.main()
