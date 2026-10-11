"""Publish reviewed QA outputs, never execute artifact contents. GITHUB_TOKEN stays in gh env."""
import hashlib, json, os, re, shutil, subprocess, tempfile, urllib.request
from pathlib import Path
from datetime import datetime, timezone

REPO='texas359-art/living-siege-qa'
ROOT=Path.cwd(); CONFIG=json.loads((ROOT/'publication/config.json').read_text())
HISTORY=ROOT/'qa-results'; HISTORY.mkdir(exist_ok=True)
WORKFLOWS={'Bastion Blender asset pipeline':('models','bastion-blender-models'), 'Bastion real WebGL visual QA':('scene','bastion-real-webgl-evidence')}

def gh(*args,check=True):
    p=subprocess.run(['gh',*args],capture_output=True,text=True)
    if check and p.returncode:raise RuntimeError('GitHub operation failed: '+p.stderr[-1500:])
    return p

def api(endpoint):return json.loads(gh('api',endpoint).stdout)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def safe_text(p):
    s=p.read_text()
    for pat in [r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'-----BEGIN .*PRIVATE KEY-----',r'(?i)authorization\s*:\s*bearer']:
        if re.search(pat,s):raise RuntimeError('Potential secret in approved text asset '+p.name)

def anonymous(url):
    # Deliberately no token, cookies or Authorization. Do not persist expiring redirect URLs.
    req=urllib.request.Request(url,headers={'User-Agent':'living-siege-public-qa-verifier','Range':'bytes=0-1023'})
    with urllib.request.urlopen(req,timeout=60) as r:
        prefix=r.read(1024)
        if r.status not in (200,206) or not prefix:raise RuntimeError('Anonymous download failed')
        if 'text/html' in r.headers.get('Content-Type',''):raise RuntimeError('Download unexpectedly requires an HTML page')
        return {'status':r.status,'first_bytes':len(prefix),'checked_at':datetime.now(timezone.utc).isoformat()}

def publish(run_id):
    run=api(f'repos/{REPO}/actions/runs/{int(run_id)}')
    if run['name'] not in WORKFLOWS:raise RuntimeError('Untrusted workflow')
    if run['head_repository']['full_name']!=REPO or run['head_branch']!='main' or run['event'] not in ['push','workflow_dispatch']:raise RuntimeError('Untrusted run source')
    if run['status']!='completed':raise RuntimeError('Run is not complete')
    kind,artifact_name=WORKFLOWS[run['name']]
    publication_commit=api(f'repos/{REPO}/git/ref/heads/main')['object']['sha']
    tag=f"qa-{run['id']}-a{run['run_attempt']}-{run['head_sha'][:12]}"
    record_path=HISTORY/(tag+'.json')
    existing=gh('release','view',tag,'-R',REPO,'--json','isDraft',check=False)
    if existing.returncode==0 and not json.loads(existing.stdout)['isDraft']:
        if record_path.exists():return json.loads(record_path.read_text())
        # Recovery from successful release publication before index commit. Never overwrite assets.
        with tempfile.TemporaryDirectory() as d:
            gh('release','download',tag,'-R',REPO,'-p','build.json','-D',d)
            record=json.loads((Path(d)/'build.json').read_text())
            if record['run_id']!=run['id'] or record['commit_sha']!=run['head_sha']:raise RuntimeError('Existing release identity mismatch')
            for a in record['assets'].values():anonymous(a['url'])
            write(record_path,record);return record
    with tempfile.TemporaryDirectory() as d:
        temp=Path(d);source=temp/'input';out=temp/'release';source.mkdir();out.mkdir()
        artifacts=api(f'repos/{REPO}/actions/runs/{run["id"]}/artifacts')['artifacts']
        selected=[a for a in artifacts if a['name']==artifact_name and not a['expired']]
        if selected:gh('run','download',str(run['id']),'-R',REPO,'-n',artifact_name,'-D',str(source))
        elif run['conclusion']=='success':raise RuntimeError('Successful run has no unexpired evidence; do not regenerate historical proof')
        files=list(source.rglob('*'))
        def find(name):return next((p for p in files if p.is_file() and p.name==name),None)
        report_name='webgl-report.json' if kind=='models' else 'report.json'
        report_file=find(report_name)
        report=json.loads(report_file.read_text()) if report_file else {'result':'NO_REPORT','errors':['Run produced no QA report. See exact Actions run.']}
        if run['conclusion']=='success' and report.get('result')!='PASS':raise RuntimeError('Successful workflow does not contain a PASS QA report')
        # Publish only asset/report allowlists; never publish logs, browser profiles or credentials.
        if kind=='models':
            names=['manifest.json','create_bastion.py']+[n+ext for n in ['tower','forge','sentinel','raider'] for ext in ['.glb','.blend']]
            names += [n+'-webgl-'+v+'.png' for n in ['tower','forge','sentinel'] for v in ['front','side','game']]
            names += ['tower-'+state+'.png' for state in ['Idle','Walk','Attack','Hit','Death']]
        else:
            names=['battle.mp4','walk-attack.mp4','all-animations.mp4','live-battle.mp4','live-walk-attack.mp4','animation-timeline.json','Idle.png','Walk.png','Attack.png','Hit.png','Death.png','Battle.png','mobile-viewport.png','desktop-diagnostics.png']
            names += ['bastion-'+n+'.glb' for n in ['tower','forge','sentinel','raider']]
        for name in names:
            p=find(name)
            if p:
                if p.is_symlink():raise RuntimeError('Symlink not allowed')
                shutil.copyfile(p,out/name)
        # Remove diagnostics describing local/browser paths; retain rendering facts and errors.
        report.get('security',{}).pop('actualArguments',None);report.pop('arguments',None)
        write(out/report_name,report)
        for p in out.glob('*.json'):safe_text(p)
        if (out/'create_bastion.py').exists():safe_text(out/'create_bastion.py')
        if kind=='models' and run['conclusion']=='success':
            from PIL import Image,ImageDraw
            montage=Image.new('RGB',(1080,1155),'#15212d');draw=ImageDraw.Draw(montage)
            for y,n in enumerate(['tower','forge','sentinel']):
                for x,v in enumerate(['front','side','game']):
                    im=Image.open(out/(n+'-webgl-'+v+'.png'));im.thumbnail((360,360));montage.paste(im,(x*360,y*385+25));draw.text((x*360+12,y*385+8),n+' / '+v,fill='white')
            montage.save(out/'design-variants.png')
        (out/'known-issues.md').write_text((ROOT/'publication/KNOWN_ISSUES.md').read_text())
        base=f'https://github.com/{REPO}/releases/download/{tag}/'
        assets={p.name:{'url':base+p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir())}
        record={'schema_version':1,'kind':kind,'run_id':run['id'],'run_attempt':run['run_attempt'],'commit_sha':run['head_sha'],'workflow':run['name'],'publication_commit':publication_commit,'tag_target_role':'publication snapshot; tested source is commit_sha','tested_source_archive_url':f'https://github.com/{REPO}/archive/{run["head_sha"]}.tar.gz','created_at':run['created_at'],'completed_at':run['updated_at'],'status':run['conclusion'],'qa_result':report.get('result'),'art_status':CONFIG['art_status'],'release_tag':tag,'release_url':f'https://github.com/{REPO}/releases/tag/{tag}','actions_url':run['html_url'],'scene_url':report.get('url',CONFIG['scene_url']),'site_source_commit':CONFIG['site_source_commit'],'site_version':CONFIG['site_version'],'scene_is_mutable':True,'artifact_provenance':[{'id':a['id'],'name':a['name'],'digest':a.get('digest')} for a in selected],'assets':assets,'model_hashes':{p.stem.removeprefix('bastion-'):sha(p) for p in out.glob('*.glb')},'model_run_id':CONFIG['model_run_id'] if not report.get('modelFiles') else None,'capture':report.get('frameCapture'),'errors':report.get('errors',[])}
        write(out/'build.json',record)
        payload=list(out.iterdir())
        (out/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(payload)))
        body=f'''# Bastion QA {run['id']} / attempt {run['run_attempt']}

- Kind: {kind}; workflow/QA status: {run['conclusion']} / {report.get('result')}
- Tested source commit: `{run['head_sha']}`
- Release tag points to publication commit: `{publication_commit}` (not the tested source).
- [Exact tested source archive](https://github.com/{REPO}/archive/{run['head_sha']}.tar.gz)
- Completed UTC: {run['updated_at']}
- [Exact Actions run]({run['html_url']})
- [Current scene (mutable)]({record['scene_url']})
- Artistic approval: {CONFIG['art_status']}.

Frozen proof is attached to this tag. Older releases/assets are never replaced by this publisher. Read build.json, SHA256SUMS.txt, {report_name}, known-issues.md. The scene URL can change independently; ?v= does not freeze it. Fixed-step WebGL MP4s and live SwiftShader recordings are explicitly distinguished. No tokens or logs are attached.
'''
        notes=temp/'notes.md';notes.write_text(body)
        if existing.returncode!=0:gh('release','create',tag,'-R',REPO,'--target',publication_commit,'--title',f'Bastion QA {run["id"]} · {kind} · {run["conclusion"]}','--notes-file',str(notes),'--draft','--prerelease')
        uploaded=json.loads(gh('release','view',tag,'-R',REPO,'--json','assets').stdout)['assets']
        uploaded_names={a['name'] for a in uploaded}
        for p in out.iterdir():
            if p.name not in uploaded_names:gh('release','upload',tag,str(p),'-R',REPO) # never --clobber
        gh('release','edit',tag,'-R',REPO,'--draft=false')
        checks={name:anonymous(asset['url']) for name,asset in assets.items()}
        anonymous(base+'build.json');anonymous(base+'SHA256SUMS.txt')
        # Verification is kept in Git history rather than changing published build.json.
        record['anonymous_checks']=checks
        write(record_path,record)
        print(f'PUBLISHED {tag}: {len(assets)} anonymous public assets',flush=True)
        return record

def update_index():
    records=sorted([json.loads(p.read_text()) for p in HISTORY.glob('qa-*.json')],key=lambda x:(x['created_at'],x['run_attempt']))
    latest=records[-1];models=[r for r in records if r['kind']=='models' and r['status']=='success'];scenes=[r for r in records if r['kind']=='scene' and r['status']=='success']
    scene=scenes[-1] if scenes else None
    compatible=[m for m in models if scene and scene.get('model_hashes') and all(m['model_hashes'].get(n)==h for n,h in scene['model_hashes'].items())]
    model=compatible[-1] if compatible else next((m for m in reversed(models) if scene and m['run_id']==scene.get('model_run_id')),models[-1] if not scene and models else None)
    index={'schema_version':1,'updated_at':datetime.now(timezone.utc).isoformat(),'latest_attempt':latest,'latest_successful_scene':scene,'related_model_build':model,'model_hash_match':bool(compatible),'history':[{'run_id':r['run_id'],'commit_sha':r['commit_sha'],'status':r['status'],'release_url':r['release_url'],'record_url':f'https://raw.githubusercontent.com/{REPO}/main/qa-results/{r["release_tag"]}.json'} for r in reversed(records)]}
    write(ROOT/'QA_LATEST.json',index)
    lines=['# Последние результаты QA · Бастион','',f'Обновлено UTC: {index["updated_at"]}. Художественный статус: **{CONFIG["art_status"]}**.','',f'[Машиночитаемый индекс](https://raw.githubusercontent.com/{REPO}/main/QA_LATEST.json). Прямые ссылки ниже публичны; файлы Release проверены без cookies и Authorization.','',f'Последняя попытка: [{latest["run_id"]}]({latest["actions_url"]}) · **{latest["status"]}** · `{latest["commit_sha"]}`.','']
    def links(r,names):
        for label,name in names:
            if name in r['assets']:lines.append(f'- [{label}]({r["assets"][name]["url"]})')
            else:lines.append(f'- {label}: отсутствует в этом историческом запуске; не подменён новым файлом.')
    if scene:
        lines += ['## Последняя успешная проверка опубликованной сцены','',f'- [Текущая тестовая сцена]({scene["scene_url"]}) — изменяемый адрес; исторические доказательства закреплены в Release.',f'- [Конкретная сборка / Release]({scene["release_url"]})',f'- [Успешный GitHub Actions]({scene["actions_url"]})',f'- Run ID: `{scene["run_id"]}` · attempt `{scene["run_attempt"]}` · дата UTC `{scene["completed_at"]}`',f'- QA source commit: `{scene["commit_sha"]}` · заявленный source commit сайта: `{scene["site_source_commit"]}`.',f'- [Метаданные и SHA256](https://github.com/{REPO}/releases/download/{scene["release_tag"]}/build.json)',f'- [Контрольные суммы файлов](https://github.com/{REPO}/releases/download/{scene["release_tag"]}/SHA256SUMS.txt)',f'- [Исходники точного проверенного QA commit](https://github.com/{REPO}/archive/{scene["commit_sha"]}.tar.gz) — tag Release обозначает публикацию, а не этот source commit.','']
        links(scene,[('Бой 20 секунд — MP4, покадровый WebGL','battle.mp4'),('Настоящая живая запись боя SwiftShader — MP4','live-battle.mp4'),('Ходьба и атака — MP4','walk-attack.mp4'),('Idle / Walk / Attack / Hit / Death — MP4','all-animations.mp4'),('Временные интервалы анимаций','animation-timeline.json'),('Крупный кадр персонажа','Idle.png'),('Кадр настоящего боя','Battle.png'),('Мобильный viewport','mobile-viewport.png'),('Отчёт ошибок и проверки','report.json'),('Известные недостатки','known-issues.md')])
        lines += ['', '**Важно:** покадровые MP4 сняты из настоящей WebGL-сцены с шагом симуляции; они не подтверждают realtime FPS. Живая запись опубликована отдельно. Технический PASS не является художественным утверждением.','']
    if model:
        lines += ['## Связанные модели и реальные ракурсы','',f'[Release моделей]({model["release_url"]}) · [успешный Blender / WebGL Actions]({model["actions_url"]}).',f'Run `{model["run_id"]}` · commit `{model["commit_sha"]}` · UTC `{model["completed_at"]}`.','',f'Совпадение GLB с ответами, реально загруженными в сцене: **{index["model_hash_match"]}**. Для старых запусков без захваченных GLB связь указана явно; криптографическая проверка не заявляется.','']
        links(model,[('Сравнение трёх дизайнов, девять реальных ракурсов','design-variants.png'),('Спереди — выбранный Бастион','tower-webgl-front.png'),('Сбоку — выбранный Бастион','tower-webgl-side.png'),('Игровой ракурс — выбранный Бастион','tower-webgl-game.png'),('Выбранный Бастион — GLB','tower.glb'),('Выбранный Бастион — Blender','tower.blend'),('Кузнец — GLB','forge.glb'),('Кузнец — Blender','forge.blend'),('Страж — GLB','sentinel.glb'),('Страж — Blender','sentinel.blend'),('Противник — GLB','raider.glb'),('Противник — Blender','raider.blend'),('Исходник bpy','create_bastion.py'),('Отчёт WebGL моделей','webgl-report.json')])
    lines += ['','## История — ссылки не перезаписываются','']
    for r in reversed(records):lines.append(f'- [{r["run_id"]} / attempt {r["run_attempt"]} · {r["kind"]} · {r["status"]}]({r["release_url"]}) · `{r["commit_sha"]}` · UTC {r["completed_at"]}')
    lines += ['','Основная игра не заменена. Подробный процесс: [publication/README.md](publication/README.md).','']
    (ROOT/'QA_LATEST.md').write_text('\n'.join(lines))

if __name__=='__main__':
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    ids=[event['workflow_run']['id']] if event.get('workflow_run') else CONFIG['bootstrap_runs']
    if os.environ.get('INPUT_RUN_ID'):ids=[int(os.environ['INPUT_RUN_ID'])]
    for run_id in ids:publish(run_id)
    update_index()
