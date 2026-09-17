import json, urllib.request
from pathlib import Path

CFG=Path('CEREBRON_REGISTRY.json')
DEFAULT='https://raw.githubusercontent.com/dmaillot95-ui/cerebron-omega-encyclopedia/main/registry/manifest.json'

def _get(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode('utf-8')

def load_registry(categories):
    meta={'loaded':False,'version':None,'categories':[],'errors':[],'provenance':[]}
    chunks=[]
    try:
        cfg=json.loads(CFG.read_text(encoding='utf-8')) if CFG.exists() else {}
        manifest_url=cfg.get('registry',DEFAULT)
        manifest=json.loads(_get(manifest_url))
        meta['version']=manifest.get('version')
        base=manifest_url.rsplit('/registry/manifest.json',1)[0]
        paths=manifest.get('paths',{})
        for cat in categories:
            p=paths.get(cat)
            if not p:
                meta['errors'].append(f'missing_path:{cat}'); continue
            url=f'{base}/{p}'
            try:
                text=_get(url)
                chunks.append(f'\n### CEREBRON_REGISTRY::{cat}\n{text[:12000]}')
                meta['categories'].append(cat)
                meta['provenance'].append(url)
            except Exception as e:
                meta['errors'].append(f'{cat}:{type(e).__name__}:{e}')
        meta['loaded']=bool(meta['categories'])
    except Exception as e:
        meta['errors'].append(f'manifest:{type(e).__name__}:{e}')
    return '\n'.join(chunks), meta
