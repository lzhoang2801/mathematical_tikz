"""Preview embeds renders, escapes TikZ and survives artifact cleanup."""
import base64
from html.parser import HTMLParser

import pytest

from evaluation.tikz_preview import write_preview


@pytest.mark.parametrize('compiled', [True, False])
def test_preview_is_self_contained_and_keeps_source_inert(tmp_path, compiled):
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
    image = tmp_path / 'render.png'
    image.write_bytes(png)
    source = r'% Tiếng Việt: góc vuông; $A_1$ </code><script>bad()</script>'
    target = {'image_path': str(image), 'tikz': source}
    output = target if compiled else {'tikz': source, 'compile': {'diagnostic': 'Undefined <command>'}}
    scores = {'compile': int(compiled), 'mathematical_correctness': 93.75 if compiled else 0,
              'content_coverage': 100.0 if compiled else 0, 'visual_readability': 83.33 if compiled else 0}
    path = write_preview(target, output, scores, tmp_path / 'preview.html')
    image.unlink()
    document = path.read_text(encoding='utf-8')
    assert 'Tiếng Việt' in document and '&lt;script&gt;' in document
    class Tags(HTMLParser):
        def __init__(self):
            super().__init__()
            self.items = []
        def handle_starttag(self, tag, attrs):
            self.items.append((tag, dict(attrs)))
    tags = Tags()
    tags.feed(document)
    images = [attrs for tag, attrs in tags.items if tag == 'img']
    assert len(images) == (2 if compiled else 1)
    assert all(base64.b64decode(attrs['src'].split(',', 1)[1]) == png for attrs in images)
    assert not any(tag == 'script' for tag, _ in tags.items)
    assert sum(tag == 'details' for tag, _ in tags.items) == 2
    assert ('93.75%' if compiled else 'Undefined &lt;command&gt;') in document
