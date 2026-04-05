#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2026 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys
import unittest

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOTDIR)
from gallery_dl.extractor.utils import twitter_article  # noqa E402


class TestTwitterArticle(unittest.TestCase):

    def test_to_document_allows_missing_cover_media(self):
        html = "".join(twitter_article.to_document({
            "title": "Example",
            "content_state": {
                "entityMap": [],
                "blocks": [],
            },
            "media_entities": [],
        }))

        self.assertIn("<h1>Example</h1>", html)
        self.assertNotIn('class="cover"', html)

    def test_process_text_applies_multiple_replacements_and_styles(self):
        html = []

        twitter_article.process_text(html, {
            "text": "Hi @ab https://t.co/x",
            "data": {
                "mentions": [{
                    "fromIndex": 3,
                    "toIndex": 6,
                    "text": "ab",
                }],
                "urls": [{
                    "fromIndex": 7,
                    "toIndex": 21,
                    "text": "https://example.com",
                }],
            },
            "inlineStyleRanges": [{
                "offset": 3,
                "length": 3,
                "style": "BOLD",
            }],
        })

        self.assertEqual(
            html[0],
            'Hi <b><a href="https://x.com/@ab">@ab</a></b> '
            '<a href="https://example.com">https://example.com</a>',
        )

    def test_stylesheet_uses_valid_math_display_rule(self):
        self.assertIn("math{display:block;}", twitter_article.STYLESHEET)


if __name__ == "__main__":
    unittest.main()
