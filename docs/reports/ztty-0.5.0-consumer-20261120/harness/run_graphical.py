#!/usr/bin/python3
"""Run the original suite GUI checks with an explicit new backend option."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import sys
import traceback

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source",type=Path,required=True)
parser.add_argument("--archive",type=Path,required=True)
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
receipt_path=args.output/"adapter.json"
if receipt_path.exists():
    raise SystemExit("graphical acceptance output already exists")
fixture=args.source/"scripts/verify_graphical.py"
spec=importlib.util.spec_from_file_location("original_suite_graphical",fixture)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
original_popen=m.subprocess.Popen
original_run=m.run
launches=[]
receipt={"schema":1,"original_fixture":str(fixture),
         "fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),
         "adapter_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "scope":"Original verify_graphical assertions; one launcher adds --backend x11. Private SHELL=/bin/sh verifies that the suite still selects its own zsh. No installed user profile is used.",
         "environment":{"SHELL":os.environ.get("SHELL"),"LIBGL_ALWAYS_SOFTWARE":os.environ.get("LIBGL_ALWAYS_SOFTWARE")}}
def popen(argv,*a,**kw):
    if isinstance(argv,(list,tuple)) and len(argv)>1 and argv[1]=="terminal":
        expected=["terminal","--name","oh-my-ztty-verify","--geometry","100x28"]
        if list(argv[1:])!=expected:
            raise RuntimeError("upstream graphical launcher changed; re-review required")
        argv=[argv[0],"terminal","--backend","x11",*argv[2:]]
        receipt["actual_launcher_argv"]=[str(x) for x in argv]
        receipt["backend_injection_count"]=receipt.get("backend_injection_count",0)+1
    p=original_popen(argv,*a,**kw)
    if isinstance(argv,(list,tuple)) and len(argv)>1 and argv[1]=="terminal":
        launches.append(p)
    return p
def traced_run(argv,env,*a,**kw):
    try:
        result=original_run(argv,env,*a,**kw)
    except m.subprocess.CalledProcessError as e:
        receipt.setdefault("failed_commands",[]).append({"command":[str(x) for x in argv],"exit_code":e.returncode,
            "stdout":e.stdout,"stderr":e.stderr})
        raise
    text=[str(x) for x in argv]
    if len(text)==4 and text[1:]==["ztty","info","oh-my-ztty-verify"]:
        session=m.find_session(json.loads(result.stdout))
        if session is not None:
            if int(session["broker_pid"])!=m.peer_pid(env["OMZTTY_SOCKET"]):
                raise RuntimeError("owned session peer mismatch")
            exe=os.readlink(f'/proc/{int(session["pid"])}/exe')
            receipt["owned_shell"]={"pid":int(session["pid"]),"executable":exe}
            if Path(exe).name!="zsh":
                raise RuntimeError("explicit backend did not retain the preset zsh")
    if len(text)>=4 and text[0]=="import" and text[1]=="-window":
        p=original_run(["xprop","-id",text[2],"_ZTTY_RENDERER","_ZTTY_GPU_DRIVER"],env)
        value=re.search(r'_ZTTY_RENDERER[^=]*=\s*"([^"]*)"',p.stdout)
        receipt["renderer"]={"window":text[2],"raw":p.stdout,"actual":value[1] if value else None}
        if not value or value[1]!="software":
            raise RuntimeError("forced-software private environment did not use the software renderer")
        shot=Path(text[-1])
        receipt["screenshot_sha256"]=hashlib.sha256(shot.read_bytes()).hexdigest()
    return result
m.subprocess.Popen=popen
m.run=traced_run
try:
    sys.argv=[str(fixture),str(args.archive),"--output",str(args.output),"--samples","1"]
    m.main()
    assert receipt.get("backend_injection_count")==1
    assert receipt.get("owned_shell")
    assert receipt.get("renderer",{}).get("actual")=="software"
    receipt["ok"]=True
except BaseException as e:
    receipt["ok"]=False
    receipt["error"]=type(e).__name__+": "+str(e)
    receipt["traceback"]=traceback.format_exc()
    raise
finally:
    m.subprocess.Popen=original_popen
    m.run=original_run
    receipt["launchers"]=[]
    for p in launches:
        item={"pid":p.pid,"returncode":p.poll()}
        if p.stderr is not None:
            try:
                if select.select([p.stderr],[],[],0)[0]:
                    item["stderr_tail"]=os.read(p.stderr.fileno(),65536).decode("utf-8","replace")
            except (OSError,ValueError):
                pass
        receipt["launchers"].append(item)
    receipt["fixture_hash_unchanged"]=hashlib.sha256(fixture.read_bytes()).hexdigest()==receipt["fixture_sha256"]
    receipt_path.write_text(json.dumps(receipt,indent=2)+"\n")
