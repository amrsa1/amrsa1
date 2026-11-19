"""Give generated statistics the same frame and spacing as the project cards."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)


def freeze_animations(card):
    """Keep final values visible in viewers that do not run CSS animations."""
    rank_offset = None
    for style in card.iter(f'{{{SVG}}}style'):
        css = style.text or ''
        match = re.search(
            r'@keyframes rankAnimation.*?to\s*{\s*stroke-dashoffset:\s*([\d.]+)',
            css, re.S,
        )
        if match:
            rank_offset = match.group(1)
        while '@keyframes' in css:
            start = css.index('@keyframes')
            end = css.index('{', start) + 1
            depth = 1
            while depth:
                if css[end] == '{':
                    depth += 1
                elif css[end] == '}':
                    depth -= 1
                end += 1
            css = css[:start] + css[end:]
        css = re.sub(
            r'\b(?:animation(?:-[\w-]+)?|transform-origin|transform)\s*:[^;{}]+;',
            '', css,
        )
        visible = '.stagger { opacity: 1; }'
        style.text = css if visible in css else css + '\n' + visible + '\n'
    for element in card.iter():
        classes = element.get('class', '').split()
        if 'rank-circle' in classes:
            offset = rank_offset or element.get('stroke-dashoffset')
            if offset is None:
                raise ValueError('Cannot determine the final rank circle state')
            element.set('stroke-dashoffset', offset)
            element.set('transform', 'rotate(-90 -10 8)')
        if 'rank-text' in classes:
            element.set('transform', 'translate(-5 5)')


for theme, background, border in [
    ('light', '#f6f8fa', '#d8dee4'),
    ('dark', '#151b23', '#30363d'),
]:
    for name in ('overview', 'languages'):
        path = Path(f'assets/stats/{name}-{theme}.svg')
        card = ET.parse(path).getroot()
        # Accept an already framed card so local styling can be rerun safely.
        if card.get('aria-label') in {'GitHub activity and rank', 'Most used languages'}:
            card = card.find(f'{{{SVG}}}svg')
            if card is None:
                raise ValueError(f'Missing generated card inside {path}')
        text = ' '.join(card.itertext())
        if 'Something went wrong' in text or 'Could not fetch' in text:
            raise ValueError(f'Refusing to publish a failed stats card: {path}')
        freeze_animations(card)
        if card.get('viewBox'):
            _, _, source_width, source_height = map(float, card.get('viewBox').split())
        else:
            source_width = float(card.attrib['width'].removesuffix('px'))
            source_height = float(card.attrib['height'].removesuffix('px'))
        height = source_height * 560 / source_width
        if height > 246:
            raise ValueError(f'Stats card exceeds its frame: {path}')
        card.attrib.update(
            x='0', y=str((248 - height) / 2), width='560', height=str(height),
            viewBox=f'0 0 {source_width} {source_height}',
        )
        frame = ET.Element(f'{{{SVG}}}svg', {
            'width': '572', 'height': '260', 'viewBox': '-6 0 572 260',
            'role': 'img',
            'aria-label': 'GitHub activity and rank' if name == 'overview' else 'Most used languages',
        })
        ET.SubElement(frame, f'{{{SVG}}}rect', {
            'x': '1', 'y': '1', 'width': '558', 'height': '246', 'rx': '12',
            'fill': background, 'stroke': border,
        })
        frame.append(card)
        output = ET.tostring(frame, encoding='unicode')
        path.write_text('\n'.join(line.rstrip() for line in output.splitlines()) + '\n')
        print(f'Styled {path}')
