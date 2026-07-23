import unittest

from check_apple_watch_listing import Listing, filter_listings_by_models, parse_watch_listings


class CheckAppleWatchListingTests(unittest.TestCase):
    def test_parse_watch_listings_extracts_unique_product_links(self):
        sample_html = r'''
        <a href="https://www.apple.com/hk/shop/product/FABC1234">Apple Watch SE 3 GPS, 40mm - Silver</a>
        <a href="https://www.apple.com/hk/shop/product/FABC1234">Apple Watch SE 3 GPS, 40mm - Silver</a>
        <script type="application/json">{"url":"https:\/\/www.apple.com\/hk\/shop\/product\/FDEF5678","title":"Apple Watch Series 10 GPS, 42mm"}</script>
        '''

        listings = parse_watch_listings(sample_html)

        self.assertEqual(2, len(listings))
        urls = {listing.url for listing in listings}
        self.assertIn("https://www.apple.com/hk/shop/product/FABC1234", urls)
        self.assertIn("https://www.apple.com/hk/shop/product/FDEF5678", urls)

    def test_filter_listings_by_models_uses_case_insensitive_matching(self):
        listings = [
            Listing(title="Apple Watch SE 3 GPS, 40mm - Midnight", url="https://example.com/1"),
            Listing(title="Apple Watch Ultra 2", url="https://example.com/2"),
        ]

        matches = filter_listings_by_models(listings, ["apple watch se 3 gps 40mm"])

        self.assertEqual([listings[0]], matches)


if __name__ == "__main__":
    unittest.main()
