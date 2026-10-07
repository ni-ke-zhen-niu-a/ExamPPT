import unittest

from examppt.core.pdf_splitter import _apply_anchor_overrides, _select_sequential_anchors
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

    def test_manual_override_moves_existing_question_start(self):
        anchors = [
            QuestionAnchor(1, 1, 56, 100, 112, "1．题目"),
            QuestionAnchor(2, 1, 56, 160, 172, "2．题目"),
            QuestionAnchor(3, 2, 56, 40, 52, "3．题目"),
        ]
        pages = [
            {"page": 1, "width": 595.3, "height": 841.9},
            {"page": 2, "width": 595.3, "height": 841.9},
        ]

        updated, warnings = _apply_anchor_overrides(
            anchors,
            pages,
            {2: {"page": 1, "top": 170.0}},
        )

        self.assertEqual(warnings, [])
        self.assertEqual(updated[1].page, 1)
        self.assertEqual(updated[1].top, 170.0)
        self.assertEqual(updated[1].bottom, 182.0)
        self.assertEqual(updated[1].text, "2．题目")

    def test_manual_override_rejects_invalid_pdf_order(self):
        anchors = [
            QuestionAnchor(1, 1, 56, 100, 112, "1．题目"),
            QuestionAnchor(2, 1, 56, 160, 172, "2．题目"),
            QuestionAnchor(3, 2, 56, 40, 52, "3．题目"),
        ]
        pages = [
            {"page": 1, "width": 595.3, "height": 841.9},
            {"page": 2, "width": 595.3, "height": 841.9},
        ]

        _, warnings = _apply_anchor_overrides(
            anchors,
            pages,
            {2: {"page": 1, "top": 90.0}},
        )

        self.assertTrue(any("must be after Q1" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
