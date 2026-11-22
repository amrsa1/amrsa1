"""Render the selected project cards from current GitHub and npm metrics."""

from concurrent.futures import ThreadPoolExecutor
from html import escape
import json
from pathlib import Path
import subprocess
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / 'assets/project-cards'
THEMES = {
    'light': ('#f6f8fa', '#d8dee4', '#1f2328', '#59636e', '#216e5e'),
    'dark': ('#151b23', '#30363d', '#f0f6fc', '#a8b3bf', '#8bd5bc'),
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def npm_downloads(package):
    url = 'https://api.npmjs.org/downloads/point/last-month/' + quote(package, safe='@/')
    with urlopen(url, timeout=20) as response:
        data = json.load(response)
    count = data['downloads']
    if data['package'] != package or type(count) is not int or count < 0:
        raise ValueError(f'Invalid npm download count for {package}')
    return package, count


def load_project(project):
    raw = subprocess.check_output(['gh', 'api', 'repos/' + project['repo']], text=True)
    data = json.loads(raw)
    project = {**project, 'metrics': data}
    with ThreadPoolExecutor(max_workers=4) as pool:
        project['downloads'] = dict(pool.map(npm_downloads, project.get('npm', [])))
    return project


def text(content, x, y, size, fill, *, weight=400, anchor='start'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(content)}</text>')


def line(x1, x2, y, stroke):
    return f'<path d="M{x1} {y}H{x2}" stroke="{stroke}"/>'


def render(project, palette, layout):
    background, border, title, body, accent = palette
    metrics = project['metrics']
    name = project['repo'].split('/')[1]
    stars, forks = metrics['stargazers_count'], metrics['forks_count']
    stars_label = f'{stars:,} {"star" if stars == 1 else "stars"}'
    forks_label = f'{forks:,} {"fork" if forks == 1 else "forks"}'
    counts = project['downloads']
    description = ' '.join(project['description'])
    accessible = f'{name}. {description} {stars_label}, {forks_label}.'
    if counts:
        downloads = ', '.join(f'{package}: {count:,}' for package, count in counts.items())
        accessible += f' npm downloads in the last month: {downloads}.'
    width = 1144 if layout == 'wide' else 560
    height = 340 if layout == 'compact' else 248
    label = project['category'].upper() + '  /  ' + metrics['language'].upper()
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width + 12}" height="{height + 12}" '
        f'viewBox="-6 0 {width + 12} {height + 12}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(name)}</title>',
        f'<desc id="desc">{escape(accessible)}</desc>',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" '
        f'fill="{background}" stroke="{border}"/>',
        f'<g font-family="{FONT}">',
        text(label, 30, 39, 13, accent, weight=650),
    ]
    if layout == 'tile':
        name_size = 27 if len(name) > 22 else 30
        title_y, description_y = 94, 140
    else:
        name_size, title_y, description_y = 38, 92, 129
    elements.append(text(name, 30, title_y, name_size, title, weight=650))
    for index, segment in enumerate(project['description']):
        elements.append(text(segment, 30, description_y + index * 25, 19, body))

    footer = height - 25
    footer_end = 520 if layout == 'wide' else width - 30
    if layout != 'compact':
        elements.append(line(30, footer_end, height - 53, border))
    else:
        footer = 190
    elements.extend([
        text(stars_label, 30, footer, 16, title, weight=650),
        text(forks_label, 139, footer, 16, title, weight=650),
    ])
    if layout == 'tile' and counts:
        count = next(iter(counts.values()))
        elements.append(text(f'{count:,} npm downloads', 250, footer, 16, accent, weight=650))
    if layout == 'wide':
        elements.append(f'<path d="M550 30V218" stroke="{border}"/>')
    if layout in ('wide', 'compact'):
        wide = layout == 'wide'
        heading_x, heading_y = (580, 39) if wide else (30, 224)
        elements.append(text('NPM DOWNLOADS · LAST MONTH', heading_x, heading_y, 13, accent, weight=650))
        elements.append(line(heading_x, width - 30, heading_y + 12, border))
        right_column = 861 if wide else 295
        column_ends = (829, 1114) if wide else (260, 530)
        row_offset, row_height = (40, 36) if wide else (35, 22)
        for index, (package, count) in enumerate(counts.items()):
            column, row = divmod(index, 4)
            y = heading_y + row_offset + row * row_height
            elements.append(text(package, (heading_x, right_column)[column], y, 17, body))
            elements.append(text(f'{count:,}', column_ends[column], y, 17, title, weight=650, anchor='end'))
    arrow_x = width - 48
    arrow_y = footer - 11 if layout == 'tile' else 29
    elements.extend([
        '</g>',
        f'<path d="M{arrow_x} {arrow_y + 11}l11-11m-10 0h10v10" fill="none" '
        f'stroke="{accent}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
        '</svg>',
    ])
    return '\n'.join(elements) + '\n'


def main():
    projects = json.loads((ROOT / 'scripts/projects.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        projects = list(pool.map(load_project, projects))
    for project in projects:
        name = project['repo'].split('/')[1]
        layouts = ('wide', 'compact') if len(project['downloads']) > 1 else ('tile',)
        for theme, palette in THEMES.items():
            directory = CARDS / 'dark' if theme == 'dark' else CARDS
            for layout in layouts:
                suffix = '-compact' if layout == 'compact' else ''
                (directory / f'{name}{suffix}.svg').write_text(render(project, palette, layout))
        print(f'Refreshed {project["repo"]}')


if __name__ == '__main__':
    main()
