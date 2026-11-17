"""Give generated statistics the same frame and spacing as the project cards."""

from pathlib import Path
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)

for theme, background, border in [
    ('light', '#f6f8fa', '#d8dee4'),
    ('dark', '#151b23', '#30363d'),
]:
    for name in ('overview', 'languages'):
        path = Path(f'assets/stats/{name}-{theme}.svg')
        card = ET.parse(path).getroot()
        text = ' '.join(card.itertext())
        if 'Something went wrong' in text or 'Could not fetch' in text:
            raise ValueError(f'Refusing to publish a failed stats card: {path}')
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
            'role': 'img', 'aria-label': 'GitHub activity and rank' if name == 'overview' else 'Most used languages',
        })
        ET.SubElement(frame, f'{{{SVG}}}rect', {
            'x': '1', 'y': '1', 'width': '558', 'height': '246', 'rx': '12',
            'fill': background, 'stroke': border,
        })
        frame.append(card)
        ET.ElementTree(frame).write(path, encoding='unicode')
        with path.open('a') as output:
            output.write('\n')
        print(f'Styled {path}')
