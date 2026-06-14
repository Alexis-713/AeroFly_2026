import unittest
from unittest.mock import patch, mock_open
from file_manager import FileManager  # Changer le nom et le changer aussi dans le programme

class TestFileManager(unittest.TestCase):

    @patch('file_manager.open', new_callable=mock_open, read_data="{}")
    @patch('file_manager.os.listdir', return_value=[])
    def test_combinaison_complete(self, mock_listdir, mock_file):
        # 1. Initialisation avec un environnement vide moked
        manager = FileManager('test_log.json')
        
        # 2. Test du premier appel (Nominal)
        res1 = manager.new_jpg_fn("image")
        self.assertEqual(res1, "image.jpg")
        
        # 3. Test du second appel (Duplication)
        res2 = manager.new_jpg_fn("image")
        self.assertEqual(res2, "image_1.jpg") # C'est ici qu'on a le '_' et le chiffre !

    @patch('file_manager.open', new_callable=mock_open, read_data="{}")
    def test_exception_si_none(self, mock_file):
        manager = FileManager('test_log.json')
        # On vérifie que l'exception est bien levée
        with self.assertRaises(Exception):
            manager.new_filename(None)

if __name__ == '__main__':
    unittest.main(verbosity=2)