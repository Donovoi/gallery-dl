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
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gallery_dl import exception  # noqa E402
from gallery_dl.extractor import facebook, imageshack, patreon  # noqa E402


class DummyPatreonExtractor(patreon.PatreonExtractor):
    subcategory = "test"
    pattern = r"patreon:test$"

    def posts(self):
        return ()


class TestReviewFeedback(unittest.TestCase):

    def test_facebook_post_without_fbid_aborts_extraction(self):
        extr = facebook.FacebookSetExtractor.from_url(
            "https://www.facebook.com/example/posts/abc"
        )

        with patch.object(
                extr, "request", return_value=SimpleNamespace(text="")), \
                patch.object(extr, "parse_post_page", return_value={
                    "set_id": None,
                    "post_photo": "https://www.facebook.com/photo/",
                }):
            with self.assertRaises(exception.AbortExtraction):
                extr.items()

    def test_patreon_content_uses_data_media_id(self):
        extr = DummyPatreonExtractor.from_url("patreon:test")

        with patch.object(extr, "_filename", return_value=None):
            result = list(extr._content({
                "content": (
                    '<div><figure><img src="https://example.org/test.png" '
                    'data-media-id="12345"/></figure></div>'
                ),
            }))

        self.assertEqual(result[0][1]["media_id"], "12345")

    def test_imageshack_request_api_strips_leading_slash(self):
        extr = imageshack.ImageshackImageExtractor.from_url(
            "https://imageshack.com/i/abc123"
        )

        with patch(
            "gallery_dl.extractor.imageshack.time.time",
            return_value=1234567890,
        ):
            with patch.object(
                extr, "request_json", return_value={"result": {}}
            ) as request_json:
                extr.request_api("/v2/images/abc123", {})

        self.assertEqual(
            request_json.call_args.args[0],
            "https://imageshack.com/rest_api/v2/images/abc123",
        )


if __name__ == "__main__":
    unittest.main()
