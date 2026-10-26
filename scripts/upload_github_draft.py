"""Upload verified assets by draft release ID, including before its tag exists."""
from pathlib import Path
import hashlib
import os
import requests


def main():
    root = Path(__file__).resolve().parents[1]
    version = (root/'VERSION').read_text().strip()
    repository = os.environ['GITHUB_REPOSITORY']
    release_id = int(os.environ['RELEASE_ID'])
    session = requests.Session()
    session.headers.update({'Authorization': 'Bearer '+os.environ['GH_TOKEN'],
                            'Accept': 'application/vnd.github+json'})
    api = 'https://api.github.com/repos/'+repository
    response = session.get(f'{api}/releases/{release_id}', timeout=30)
    response.raise_for_status()
    release = response.json()
    if not release['draft'] or release['tag_name'] != 'v'+version:
        raise RuntimeError('Refusing to replace assets outside the intended draft')
    existing = {asset['name']: asset for asset in release['assets']}
    output = root/'.release'
    names = [line.split('  ', 1)[1] for line in (output/'SHA256SUMS.txt').read_text().splitlines()]
    for name in names+['SHA256SUMS.txt']:
        path = output/name
        if path.parent.resolve() != output.resolve():
            raise RuntimeError('Invalid release asset path')
        digest = 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
        if name in existing:
            old = existing[name]
            if old.get('digest') == digest and old['state'] == 'uploaded':
                continue
            response = session.delete(f"{api}/releases/assets/{old['id']}", timeout=30)
            response.raise_for_status()
        with path.open('rb') as stream:
            response = session.post(f'https://uploads.github.com/repos/{repository}/releases/{release_id}/assets',
                                    params={'name':name}, data=stream,
                                    headers={'Content-Type':'application/octet-stream'}, timeout=(30,600))
        response.raise_for_status()
        asset = response.json()
        if asset.get('digest') != digest or asset['size'] != path.stat().st_size:
            raise RuntimeError('Uploaded asset checksum mismatch: '+name)
        print('Verified upload: '+name, flush=True)


if __name__ == '__main__':
    main()
