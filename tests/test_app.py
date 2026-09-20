import io
import unittest
from PIL import Image
from app import app, defaults, definition, parse_definition, pack, render


class ConverterTests(unittest.TestCase):
    def test_column_order_and_lsb_first(self):
        image = Image.new('1', (8, 16))
        for point in ((0, 0), (0, 7), (0, 8), (1, 1), (7, 15)):
            image.putpixel(point, 1)
        self.assertEqual(pack([image]), bytes([129, 1, 2, 0] + [0] * 11 + [128]))

    def test_definition_roundtrip(self):
        cfg = defaults()
        cfg['glyphs'][33]['hoff'] = -2.5
        self.assertEqual(parse_definition(definition(cfg).decode()), cfg)

    def test_original_decimal_comma(self):
        cfg = parse_definition('globalhoffset=-5,6\nhoff=33 1,5\n')
        self.assertEqual(cfg['globalhoffset'], -5.6)
        self.assertEqual(cfg['glyphs'][33]['hoff'], 1.5)

    def test_render_and_border(self):
        images = render(defaults())
        self.assertEqual(len(pack(images)), 6840)
        self.assertFalse(images[0].getbbox())
        self.assertTrue(images[33].getbbox())
        for image in images:
            self.assertTrue(all(not image.getpixel((23, y)) for y in range(24)))
            self.assertTrue(all(not image.getpixel((x, 23)) for x in range(24)))

    def test_included_styles(self):
        for style in ('Regular', 'Bold', 'Italic', 'Bold, Italic'):
            cfg = defaults()
            cfg['fontstyle'] = style
            self.assertTrue(render(cfg)[33].getbbox())

    def test_download_names(self):
        import json
        from PIL import ImageFont
        from pathlib import Path
        font_data = Path(ImageFont.truetype('DejaVuSans.ttf', 24).path).read_bytes()
        client = app.test_client()
        for action, extension in (('definition', 'font880'), ('binary', 'rmsfont'), ('source', 'c')):
            for width, height in ((24, 24), (16, 32)):
                response = client.post('/api/' + action, data={
                    'config': json.dumps({'bitmapwidth': width, 'bitmapheight': height}),
                    'font': (io.BytesIO(font_data), 'ghost.ttf'),
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(f'ghost-{width}x{height}.{extension}', response.headers['Content-Disposition'])
        response = client.post('/api/definition')
        self.assertIn('DejaVu-Sans-24x24.font880', response.headers['Content-Disposition'])

    def test_api(self):
        client = app.test_client()
        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.get('/health').json, {'status': 'ok'})
        self.assertEqual(client.post('/api/binary').data, pack(render(defaults())))
        self.assertIn(b'const uint8_t fontDejaVu_Sans24x24', client.post('/api/source').data)
        self.assertEqual(len(client.post('/api/preview').json['glyphs']), 95)
        self.assertEqual(client.post('/api/preview', data={'config': '{"bitmapwidth":9}'}).status_code, 400)
        self.assertEqual(client.post('/api/preview', data={'config': 'null'}).status_code, 400)
        self.assertEqual(client.post('/api/load', data={'definition': (io.BytesIO(b'hoff=95 0'), 'bad.font880')}).status_code, 400)
        self.assertEqual(client.post('/api/preview', data={'font': (io.BytesIO(b'bad'), 'bad.ttf')}).status_code, 400)
        self.assertEqual(client.post('/api/preview', data={'config': '{"fontfamily":"Arial"}'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
