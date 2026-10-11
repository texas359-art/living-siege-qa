"""Public HTTPS check after committing the index. No GitHub token or cookies used."""
import json, subprocess, urllib.request

repo='texas359-art/living-siege-qa'
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'living-siege-anonymous-index-check'}),timeout=60) as r:
        assert r.status==200
        return r.read()
fixed=f'https://raw.githubusercontent.com/{repo}/{commit}/'
md=get(fixed+'QA_LATEST.md').decode()
index=json.loads(get(fixed+'QA_LATEST.json'))
latest=get(f'https://raw.githubusercontent.com/{repo}/main/QA_LATEST.md?publication={commit}').decode()
assert '# Последние результаты QA' in latest
scene=index['latest_successful_scene']
if scene:
    assert scene['release_url'] in md
    assert scene['status']=='success'
    assert scene['commit_sha'] in md
    assert all('/releases/download/'+scene['release_tag']+'/' in a['url'] for a in scene['assets'].values())
print('PASS: public latest index and exact index commit downloadable without authentication; source/release identities consistent')
