import argparse,ctypes,hashlib,json,os,pathlib,subprocess,time
ap=argparse.ArgumentParser();ap.add_argument('--suite-sha',required=True);a=ap.parse_args()
c=pathlib.Path(__file__).resolve().parent;r=c/'source';out=c/'acceptance-v050';out.mkdir(exist_ok=False)
for d in ['bundles','tmp','base-home','runtime','graphical']:(out/d).mkdir()
(out/'runtime').chmod(0o700)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args,cwd=r):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
assert git('rev-parse','HEAD')==a.suite_sha and git('status','--porcelain=v1')==''
prep=json.loads((c/'preparation.json').read_text())
for p,h in prep['rules'].items():assert sha(r/p)==h,(p,'fixture changed')
for arch,v in prep['inputs'].items():
 for b,m in v['binaries'].items():assert sha(pathlib.Path(m['path']))==m['sha256']
pins=dict(prep['inputs']['x86_64']['BUILD']['source_commits']);pins['ztty']='c4f8f48c9598284a589e609f25242b49ceabfea8'
expected={'x86_64':{'archive':'4b79ded489c37325ac049e4962e75c7ff773c2c5d073d8fbad154bb47dfed6b2','elf':'3ed8cead1c4ca20aedd4aa262de8fe992bcf9639546d95f89f7a782eeef7a491'},'aarch64':{'archive':'f86ddc20d6359c8301e7198adf80359c067ea02c28228139e2a39705a5ddd09d','elf':'39ced58ddb1f3fd2abb2558d33949a24dc6bf8801e3809cbbda187090c10057d'}}
cg=[s.split(':',2)[2] for s in pathlib.Path('/proc/self/cgroup').read_text().splitlines() if s.startswith('0::')][0]
assert 'omztty-acceptance-v050-20261120.service' in cg
cp=pathlib.Path('/sys/fs/cgroup')/cg.lstrip('/')
assert ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)==0
initial_home=pathlib.Path.home()
def anchors():
 result={}
 for rel in prep['installed_anchors_before']:
  p=initial_home/rel;v={'exists':p.exists(),'symlink':p.is_symlink()}
  if p.is_symlink():v['target']=os.readlink(p)
  if p.exists():
   v['mode']=oct(p.lstat().st_mode&0o7777)
   if p.is_file():v['sha256']=sha(p)
  result[rel]=v
before=anchors()
env={k:v for k,v in os.environ.items() if not k.startswith(('XDG_','ZTTY_','OMZTTY_','ZSHARD_','ZDOTDIR','DBUS_STARTER')) and k not in ['DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','PYTHONPATH']}
env.update(HOME=str(out/'base-home'),PATH=str(c/'harness/bin')+':/usr/bin:/bin',TMPDIR=str(out/'tmp'),XDG_RUNTIME_DIR=str(out/'runtime'),SHELL='/bin/sh',LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',RUSTC_WRAPPER='',CARGO_BUILD_JOBS='1',SUITE_ACCEPTANCE_OUTPUT=str(out/'graphical'))
assert env.get('DBUS_SESSION_BUS_ADDRESS')
start=time.monotonic();steps=[];archives={}
record={'schema':1,'suite_source':a.suite_sha,'ztty_source':pins['ztty'],'release_id':452238617,'release_run':44668398577,'scope':'Private unreleased suite consumer candidate; VERSION remains 0.2.1; no existing installation or default terminal changed. ARM64 assembly only. No Rust compilation or AI connection.','script_sha256':sha(pathlib.Path(__file__)),'cgroup':str(cp),'private_dbus':True,'subreaper':True,'helper_hashes':{p:sha(c/p) for p in ['harness/isolated_xvfb.py','harness/bin/Xvfb','harness/run_graphical.py']},'lock_sha256':sha(r/'dependencies.lock.json')}
def step(name,argv,timeout=180):
 t=time.monotonic()
 with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
  p=subprocess.run(argv,cwd=r,env=env,stdout=stdout,stderr=stderr,timeout=timeout)
 steps.append({'name':name,'command':argv,'exit_code':p.returncode,'seconds':time.monotonic()-t,'stdout':name+'.stdout','stderr':name+'.stderr'})
 if p.returncode:raise RuntimeError(name+' failed')
def audit_archive(arch):
 import tarfile
 archive=out/'bundles'/('oh-my-ztty-0.2.1-linux-'+arch+'.tar.gz')
 assert sha(r/'.cache'/('ztty-linux-'+arch+'.tar.gz'))==expected[arch]['archive']
 with tarfile.open(archive) as tar,tarfile.open(prep['inputs'][arch]['archive']) as old:
  build=json.load(tar.extractfile('oh-my-ztty/BUILD.json'));assert build['source_commits']==pins and build['suite_version']=='0.2.1'
  manifest=tar.extractfile('oh-my-ztty/MANIFEST.sha256').read().decode().splitlines()
  changes=[]
  for line in manifest:
   digest,name=line.split('  ',1);member=tar.getmember('oh-my-ztty/'+name);assert member.isfile()
   data=tar.extractfile(member).read();actual=hashlib.sha256(data).hexdigest();assert actual==digest
   try:previous=old.extractfile('oh-my-ztty/'+name).read()
   except KeyError:previous=None
   if previous!=data:changes.append(name)
   if name.startswith(('components/zshard/','components/zrc/')) or name in ['bin/ssmcp','bin/zdot','bin/zfetch','bin/code-mode.js']:
    assert previous==data,(arch,name,'unchanged component drifted')
  ztty=tar.extractfile('oh-my-ztty/bin/ztty').read();assert hashlib.sha256(ztty).hexdigest()==expected[arch]['elf']
  archives[arch]={'path':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'manifest_files_verified':len(manifest),'BUILD':build,'ztty_elf_sha256':expected[arch]['elf'],'changed_members_from_official_suite_0_2_1':changes}
try:
 for arch in ['x86_64','aarch64']:
  step('bundle-'+arch,['/usr/bin/python3','scripts/build_bundle.py','--arch',arch,'--zdot',str(c/'inputs'/arch/'zdot'),'--zfetch',str(c/'inputs'/arch/'zfetch'),'--output',str(out/'bundles')],timeout=240)
  audit_archive(arch)
 step('smoke-x86_64',['/usr/bin/python3','scripts/smoke_bundle.py',archives['x86_64']['path']],timeout=180)
 assert 'ztty 0.5.0' in (out/'smoke-x86_64.stdout').read_text()
 step('graphical-x86_64',['/usr/bin/python3',str(c/'harness/run_graphical.py'),'--source',str(r),'--archive',archives['x86_64']['path'],'--output',str(out/'graphical')],timeout=180)
 gui=json.loads((out/'graphical/linux-x86_64-suite.json').read_text())
 adapter=json.loads((out/'graphical/adapter.json').read_text());assert adapter['ok'] and adapter['fixture_hash_unchanged']
 display=json.loads((out/'graphical/xvfb-owner.json').read_text());assert display['cleanup_complete'] and display['native_display_zero_unchanged']
 assert gui['completion_cache']['reused'] and 'ztty 0.5.0' in gui['component_versions']
 record['graphical_checks']=gui['graphical_checks'];record['component_versions']=gui['component_versions']
 record['reaped']=[]
 for _ in range(64):
  try:pid,status=os.waitpid(-1,os.WNOHANG)
  except ChildProcessError:break
  if pid:record['reaped'].append({'pid':pid,'status':status})
  else:time.sleep(0.02)
 record['adopted_children_after']=pathlib.Path(f'/proc/self/task/{os.getpid()}/children').read_text().strip()
 assert record['adopted_children_after']==''
 assert anchors()==before
 assert git('rev-parse','HEAD')==a.suite_sha and git('status','--porcelain=v1')==''
 for arch,meta in archives.items():assert sha(pathlib.Path(meta['path']))==meta['sha256']
 record['ok']=True
except BaseException as e:
 record['ok']=False;record['error']=type(e).__name__+': '+str(e)
finally:
 record.update(steps=steps,archives=archives,seconds=time.monotonic()-start,installed_anchors_unchanged=anchors()==before,source_after=git('rev-parse','HEAD'),source_status_after=git('status','--porcelain=v1'))
 record['resources']={n:(cp/n).read_text().strip() for n in ['memory.peak','memory.swap.peak','memory.events','cpu.max'] if (cp/n).exists()}
 record['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and 'tmp' not in p.relative_to(out).parts and 'base-home' not in p.relative_to(out).parts and 'runtime' not in p.relative_to(out).parts}
 (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({'ok':record['ok'],'error':record.get('error'),'result':str(out/'result.json'),'sha256':sha(out/'result.json'),'seconds':record['seconds'],'resources':record['resources']}),flush=True)
raise SystemExit(0 if record['ok'] else 1)
