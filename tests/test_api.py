import unittest
from unittest.mock import patch, Mock

from chessprep.api import get_recent_games, parse_username


class APIClientTests(unittest.TestCase):
    def test_username_urls(self):
        self.assertEqual(parse_username('https://www.chess.com/member/YenRiva'), 'yenriva')
        self.assertEqual(parse_username('wagnerstoffelnh'), 'wagnerstoffelnh')
        for bad in ['https://malicious.example/member/a', 'https://www.chess.com/analysis', 'http://chess.com/member/a', '../user']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_username(bad)

    @patch('chessprep.api.requests.Session')
    def test_fetch_and_filter(self, mock_session):
        archives = {'archives': ['https://api.chess.com/pub/player/yenriva/games/2026/09',
                                 'https://api.chess.com/pub/player/yenriva/games/2026/10']}
        game = lambda end, cls='rapid', rules='chess': {'end_time':end,'time_class':cls,'rules':rules,'pgn':'[Event "Test"]'}
        replies = [archives, {'games':[game(20,'blitz'),game(25,'rapid'),game(30,'rapid','chess960')]},
                   {'games':[game(5,'rapid')]}]
        response_objects = []
        for data in replies:
            response = Mock(status_code=200)
            response.json.return_value = data
            response_objects.append(response)
        mock_session.return_value.get.side_effect = response_objects
        result = get_recent_games('yenriva', limit=2, time_class='rapid')
        self.assertEqual([x['end_time'] for x in result], [25,5])
        called_urls = [c.args[0] for c in mock_session.return_value.get.call_args_list]
        self.assertTrue(called_urls[1].endswith('/2026/10'))
        self.assertTrue(called_urls[2].endswith('/2026/09'))


if __name__ == '__main__':
    unittest.main()
