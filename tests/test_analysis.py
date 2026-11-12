import unittest
from chessprep.api import parse_username
from chessprep.analysis import (
    parse_games, summary, frequency, common_paths, build_plan, format_moves
)


def match(white, black, moves, white_result="win", black_result="checkmated", date=1):
    from io import StringIO
    import chess.pgn
    g = chess.pgn.read_game(StringIO('''[Event "Test"]
[Site "Test"]
[Date "2026.11.01"]
[Round "-"]
[White "A"]
[Black "B"]
[Result "1-0"]

''' + moves))
    out = StringIO()
    print(g, file=out)
    return {"white":{"username":white,"rating":1200,"result":white_result},
            "black":{"username":black,"rating":1250,"result":black_result},
            "pgn":out.getvalue(),"end_time":date,"time_class":"rapid","rules":"chess","url":"https://www.chess.com/game/123"}


class ChessPrepTests(unittest.TestCase):
    def setUp(self):
        self.yours = parse_games([
            match('me', 'X', '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 1-0'),
            match('X', 'me', '1. d4 d5 2. c4 e6 1-0', date=2),
        ], 'me')
        self.theirs = parse_games([
            match('X', 'opponent', '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 1-0'),
            match('opponent', 'X', '1. d4 Nf6 2. c4 g6 1-0', date=2),
        ], 'opponent')

    def test_username(self):
        self.assertEqual(parse_username('https://www.chess.com/member/YenRiva'), 'yenriva')
        self.assertEqual(parse_username('wagnerstoffelnh'), 'wagnerstoffelnh')
        with self.assertRaises(ValueError):
            parse_username('https://evil.test/member/yenriva')
        with self.assertRaises(ValueError):
            parse_username('http://www.chess.com/member/yenriva')

    def test_result_perspective(self):
        self.assertEqual(summary(self.yours)['wins'], 1)
        self.assertEqual(summary(self.yours)['losses'], 1)
        self.assertEqual(summary(self.yours)['score_pct'], 50.0)

    def test_conditional_reply(self):
        replies, total = frequency(self.theirs, 'black', 1, ('e4',))
        self.assertEqual(total, 1)
        self.assertEqual(replies['e5'], 1)

    def test_matching_line(self):
        paths = common_paths(self.yours, self.theirs, 'white')
        self.assertTrue(any('1. e4 e5' in p['Linha'] for p in paths))
        self.assertEqual(format_moves(('e4','e5','Nf3')), '1. e4 e5 2. Nf3')

    def test_plan_grounded(self):
        plan = ' '.join(build_plan(self.yours, self.theirs, 'white'))
        self.assertIn('1. e4', plan)
        self.assertIn('1... e5 (1/1)', plan)


if __name__ == '__main__':
    unittest.main()
