import unittest

from acquire.directive import Directive

class TestDirectivesFromWiredata(unittest.TestCase):
    
    def test_single_parameterless_directive(self):
        d = Directive('GT;;:')
        self.assertTrue(d.code == 'GT', d)
        self.assertTrue(len(d.params) == 0, d)
    
    def test_single_one_parameter_directive(self):
        d = Directive('SS;4;:')
        self.assertTrue(d.code == 'SS', d)
        self.assertTrue(int(d[0]) == 4, d)
        self.assertTrue(len(d.params) == 1, d)
    
    def test_single_quoted_parameter_directive(self):
        wiredata = (
            '"Can you do the ""Otter dance""?"',
            '"""Otter dance"", can you do it?"',
            '"He said ""I cannot do the ""Otter dance."""""',
        )
        for wiredatum in wiredata:
            d = Directive('LM;%s;:' % wiredatum)
            self.assertTrue(d.code == 'LM', d)
            self.assertTrue('Otter dance' in d[0], d)
    
    
    def test_multiple_directives(self):
        ds = Directive.parse_multiple('SS;3;:GM;"What is updog?";:'
                                      'GM;"""n2m""";:GS;;:')
        self.assertTrue(len(ds) == 4, ds)
        self.assertTrue(ds[0].code == 'SS', ds[0])
        self.assertTrue(ds[1].code == 'GM', ds[1])
        self.assertTrue(ds[2].code == 'GM', ds[2])
        self.assertTrue(ds[3].code == 'GS', ds[3])
    

class TestDirectivesFromArgs(unittest.TestCase):
    
    def test_parameterless_directive(self):
        d = Directive('GT')
        self.assertTrue(d.code == 'GT', d)
        self.assertTrue(len(d.params) == 0, d)
    
    def test_parametered_directive(self):
        d = Directive('SV', 'frmTileRack', 'cmdTile', 3, 'Visible', 0)
        self.assertTrue(d.code == 'SV', d)
        self.assertTrue(d[0] == 'frmTileRack', d)
        self.assertTrue(d[2] == 3, d)
        self.assertTrue(len(d.params) == 5, d)
    

class TestWiredataConversion(unittest.TestCase):
    
    def test_parameterless_directive(self):
        d = Directive('GT')
        self.assertTrue(str(d) == 'GT;;:', d)
    
    def test_singly_parametered_directive(self):
        d = Directive('SS', 4)
        self.assertTrue(str(d) == 'SS;4;:', d)
    
    def test_triply_parametered_directive(self):
        d = Directive('AT', 1, 56, 12632256)
        self.assertTrue(str(d) == 'AT;1,56,12632256;:', d)
    
    def test_quoted_parameter(self):
        d = Directive('BM', 'Lobby', 'Who "is" dat?')
        self.assertTrue(str(d) == 'BM;Lobby,"Who ""is"" dat?";:', d)
    

if __name__ == '__main__':
    unittest.main()
