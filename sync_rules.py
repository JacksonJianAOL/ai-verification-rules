"""Build native Shadowrocket lists from public domain data only."""
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timezone
import yaml

BASE = 'https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/classical/'
SOURCES = {
    'anthropic': BASE + 'anthropic.list',
    'hcaptcha': BASE + 'hcaptcha.list',
    'cloudflare': BASE + 'cloudflare.list',
    'proxyrules': 'https://raw.githubusercontent.com/flyingparanoia/ProxyRules/main/OpenAI.yaml',
}
DOMAIN = re.compile(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$', re.I)


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'public-ai-verification-rules/1.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(1_048_577)
    if len(data) > 1_048_576:
        raise ValueError('Rule source too large')
    return data


def parse(data, classical):
    if classical:
        values = [line.strip() for line in data.decode('utf-8-sig').splitlines() if line.strip() and not line.lstrip().startswith('#')]
    else:
        document = yaml.safe_load(data)
        if not isinstance(document, dict) or not isinstance(document.get('payload'), list):
            raise ValueError('Invalid ProxyRules payload')
        values = document['payload']
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError('Non-string rule')
        value = value.strip()
        if classical:
            kind, domain = value.split(',', 1)
            if kind not in ('DOMAIN', 'DOMAIN-SUFFIX'):
                raise ValueError('Unsupported upstream rule: ' + kind)
        elif value.startswith(('+.', '*.', '.')):
            kind, domain = 'DOMAIN-SUFFIX', value[2:] if value.startswith(('+.', '*.')) else value[1:]
        elif value.startswith(('DOMAIN,', 'DOMAIN-SUFFIX,')):
            kind, domain = value.split(',', 1)
        else:
            kind, domain = 'DOMAIN', value
        domain = domain.lower()
        if not DOMAIN.fullmatch(domain):
            raise ValueError('Invalid domain entry')
        result.append((kind, domain))
    if not result:
        raise ValueError('Empty rule source; preserve last published output')
    return list(dict.fromkeys(result))


def covered(rule, earlier):
    kind, domain = rule
    for parent_kind, parent_domain in earlier:
        if parent_kind == 'DOMAIN-SUFFIX' and (domain == parent_domain or domain.endswith('.' + parent_domain)):
            return True
        if kind == 'DOMAIN' and parent_kind == 'DOMAIN' and domain == parent_domain:
            return True
    return False


def main():
    # Download and validate ALL sources before writing ANY published file.
    fetched = {name: fetch(url) for name, url in SOURCES.items()}
    parsed = {name: parse(data, name != 'proxyrules') for name, data in fetched.items()}
    meta = list(dict.fromkeys(rule for name in ('anthropic', 'hcaptcha', 'cloudflare') for rule in parsed[name]))
    extras = [rule for rule in parsed['proxyrules'] if not covered(rule, meta)]
    manual = [('DOMAIN-SUFFIX', 'withpersona.com')]
    union = list(dict.fromkeys([*meta, *extras, *manual]))
    assert covered(('DOMAIN', 'claude.ai'), union)
    assert covered(('DOMAIN', 'challenges.cloudflare.com'), union)
    assert covered(('DOMAIN', 'inquiry.withpersona.com'), union)
    assert covered(('DOMAIN', 'other.withpersona.com'), union)
    output = {name + '.list': parsed[name] for name in ('anthropic', 'hcaptcha', 'cloudflare')}
    output['proxyrules-extra.list'] = extras
    output['union.list'] = union
    texts = {name: '# Public domain routing data; no proxy policy or credentials.\n' + '\n'.join(kind + ',' + domain for kind, domain in rules) + '\n' for name, rules in output.items()}
    summary = {
        'schema': 1, 'priority': ['MetaCubeX:anthropic', 'MetaCubeX:hcaptcha', 'MetaCubeX:cloudflare', 'ProxyRules:missing-only', 'manual:withpersona.com'],
        'sources': {name: {'url': SOURCES[name], 'sha256': hashlib.sha256(data).hexdigest(), 'entries': len(parsed[name])} for name, data in fetched.items()},
        'meta_unique': len(meta), 'proxyrules_missing': len(extras), 'union_count': len(union),
        'output_sha256': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in texts.items()},
    }
    dest = Path(__file__).resolve().parent / 'rules'
    dest.mkdir(exist_ok=True)
    previous = dest / 'manifest.json'
    # Avoid unnecessary commits when source content has not changed.
    old = json.loads(previous.read_text()) if previous.exists() else None
    unchanged = old is not None and all(old.get(key) == value for key, value in summary.items())
    summary['built_at_utc'] = old['built_at_utc'] if unchanged else datetime.now(timezone.utc).isoformat()
    texts['manifest.json'] = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
    with tempfile.TemporaryDirectory(dir=dest.parent) as temporary:
        stage = Path(temporary)
        for name, content in texts.items():
            (stage / name).write_text(content)
        for name in texts:
            os.replace(stage / name, dest / name)
    print(json.dumps({key: summary[key] for key in ('meta_unique', 'proxyrules_missing', 'union_count')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
