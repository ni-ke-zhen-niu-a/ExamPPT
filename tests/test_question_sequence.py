import unittest

from examppt.core.pdf_splitter import _select_sequential_anchors
from examppt.core.question_ir import QuestionAnchor


class QuestionSequenceTests(unittest.TestCase):
    def test_selects_contiguous_sequence_and_ignores_noise(self):
        anchors = [
            QuestionAnchor(1, 1, 56, 100, 112, "1．题目"),
            QuestionAnchor(99, 1, 100, 120, 132, "99．页码噪声"),
            QuestionAnchor(2, 1, 56, 160, 172, "2．题目"),
            QuestionAnchor(3, 2, 56, 40, 52, "3．题目"),
        ]
        selected, warnings = _select_sequential_anchors(anchors)
        self.assertEqual([a.number for a in selected], [1, 2, 3])
        self.assertTrue(any("stops at Q3" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
