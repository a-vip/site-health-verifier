import unittest
from unittest.mock import patch, MagicMock
from site_health_verifier.seo_audit import RobotsTxtAuditor, inspect_url

class TestSEOAudit(unittest.TestCase):
    def test_robots_txt_matching(self):
        auditor = RobotsTxtAuditor("https://example.com")
        auditor.disallow_rules = ["/wp-admin/", "/private/"]
        
        self.assertEqual(auditor.is_path_blocked("https://example.com/wp-admin/index.php"), "/wp-admin/")
        self.assertEqual(auditor.is_path_blocked("https://example.com/private/doc.pdf"), "/private/")
        self.assertIsNone(auditor.is_path_blocked("https://example.com/public-post/"))

    @patch("urllib.request.build_opener")
    def test_inspect_url_redirect(self, mock_opener_builder):
        mock_opener = MagicMock()
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 301
        mock_resp.headers = {"Location": "https://example.com/new-url/"}
        mock_opener.open.return_value.__enter__.return_value = mock_resp
        mock_opener_builder.return_value = mock_opener

        auditor = RobotsTxtAuditor("https://example.com")
        res = inspect_url("https://example.com/old-url/", auditor)
        self.assertTrue(res["is_redirect"])
        self.assertEqual(res["redirect_target"], "https://example.com/new-url/")

if __name__ == "__main__":
    unittest.main()
