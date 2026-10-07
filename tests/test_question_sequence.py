import unittest

from examppt.core.pdf_splitter import _detect_title_from_lines, _select_sequential_anchors
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

    def test_detect_title_prefers_centered_exam_heading(self):
        lines = [
            {"text": "九年级数学月考模拟试卷2", "x0": 210.0, "x1": 386.0, "top": 56.0, "bottom": 72.0},
            {"text": "学校：____ 姓名：____ 班级：____", "x0": 120.0, "x1": 470.0, "top": 82.0, "bottom": 92.0},
            {"text": "一、单选题", "x0": 56.0, "x1": 110.0, "top": 98.0, "bottom": 108.0},
        ]

        title = _detect_title_from_lines(lines, page_width=595.3, page_height=841.9)

        self.assertEqual(title, "九年级数学月考模拟试卷2")

if __name__ == "__main__":
    unittest.main()
