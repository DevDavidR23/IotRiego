from django.test import SimpleTestCase


class CorsConfigurationTests(SimpleTestCase):
    def test_preflight_allows_local_frontend(self):
        response = self.client.options(
            '/api/promedio-diario/',
            HTTP_ORIGIN='http://localhost:3000',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Access-Control-Allow-Origin'],
            'http://localhost:3000',
        )
        self.assertIn('POST', response['Access-Control-Allow-Methods'])

    def test_cors_does_not_allow_unconfigured_origin(self):
        response = self.client.get(
            '/',
            HTTP_ORIGIN='http://example.com',
        )

        self.assertNotIn('Access-Control-Allow-Origin', response)
