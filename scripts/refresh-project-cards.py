"""Render the selected projects with current GitHub and npm counts."""

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
    'light': ('#ffffff', '#d8dee4', '#1955a5', '#475569', '#53637a'),
    'dark': ('#1a1e2e', '#343a4f', '#a4bdff', '#c0c9de', '#a3afca'),
}
LANGUAGE_COLORS = {'TypeScript': '#3178c6', 'JavaScript': '#b28514', 'Shell': '#65a84c'}
ICONS = {
    'repo': 'M4 2h8.5v10H5a2 2 0 0 0-2 2V4a2 2 0 0 1 1-2ZM3 14c0-1.1.9-2 2-2h7.5v2.5H5M6 5h4M6 8h4',
    'star': 'm8 1.9 1.8 3.7 4.1.6-3 2.9.7 4.1L8 11.3l-3.6 1.9.7-4.1-3-2.9 4.1-.6Z',
    'fork': 'M5.5 4a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Zm8 0a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Zm-4 8a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM4 5.5v1A2.5 2.5 0 0 0 6.5 9h3A2.5 2.5 0 0 0 12 6.5v-1M8 9v1.5',
    'download': 'M8 2v8m-3-3 3 3 3-3M3 11v2.5h10V11',
}


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
    metrics = json.loads(raw)
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloads = dict(pool.map(npm_downloads, project.get('npm', [])))
    return {**project, 'metrics': metrics, 'downloads': downloads}


def text(content, x, y, size, color, weight=400):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}">{escape(content)}</text>')


def icon(name, x, y, color):
    return (f'<path d="{ICONS[name]}" transform="translate({x} {y})" fill="none" '
            f'stroke="{color}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>')


def render(project, palette):
    background, border, accent, body, muted = palette
    name = project['repo'].split('/')[-1]
    metrics = project['metrics']
    language = metrics['language']
    stars = f'{metrics["stargazers_count"]:,}'
    forks = f'{metrics["forks_count"]:,}'
    package = project.get('featured_npm') or next(iter(project['downloads']), None)
    description = ' '.join(project['description'])
    summary = f'{name}. {description} {language}. GitHub stars: {stars}. Forks: {forks}.'
    if package:
        count = f'{project["downloads"][package]:,}'
        summary += f' {package} npm downloads in the last month: {count}.'

    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="416" height="125" '
        'viewBox="0 0 416 125" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(name)}</title>',
        f'<desc id="desc">{escape(summary)}</desc>',
        f'<rect x="3.5" y="4.5" width="409" height="115" rx="8" fill="{background}" stroke="{border}"/>',
        '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">',
        icon('repo', 18, 18, accent),
        text(name, 41, 31, 16, accent, 650),
    ]
    for index, segment in enumerate(project['description']):
        elements.append(text(segment, 19, 54 + index * 17, 12.5, body))

    dot = LANGUAGE_COLORS.get(language, accent)
    elements.extend([
        f'<circle cx="23" cy="98" r="4.5" fill="{dot}"/>',
        text(language, 33, 102, 12, muted),
        icon('star', 121, 90, muted),
        text(stars, 141, 102, 12, muted),
        icon('fork', 196, 90, muted),
        text(forks, 216, 102, 12, muted),
    ])
    if package:
        elements.extend([
            icon('download', 268, 90, muted),
            text(f'{count} npm / mo', 289, 102, 12, muted),
        ])
    return '\n'.join([*elements, '</g>', '</svg>', ''])


def refresh_package_table(downloads):
    readme = ROOT / 'README.md'
    start = '<!-- astur-downloads:start -->\n'
    end = '<!-- astur-downloads:end -->'
    before, table = readme.read_text().split(start)
    _, after = table.split(end)
    rows = [
        '| Package | Downloads in the last month |',
        '| :--- | ---: |',
    ]
    for package, count in downloads.items():
        rows.append(f'| [`{package}`](https://www.npmjs.com/package/{package}) | {count:,} |')
    readme.write_text(before + start + '\n'.join(rows) + '\n' + end + after)


def main():
    projects = json.loads((ROOT / 'scripts/projects.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        projects = list(pool.map(load_project, projects))
    for project in projects:
        name = project['repo'].split('/')[-1]
        for theme, palette in THEMES.items():
            directory = CARDS / 'dark' if theme == 'dark' else CARDS
            (directory / f'{name}.svg').write_text(render(project, palette))
        print(f'Refreshed {project["repo"]}')
    astur = next(project for project in projects if project['repo'] == 'Astur-mobile/Astur')
    refresh_package_table(astur['downloads'])


if __name__ == '__main__':
    main()
