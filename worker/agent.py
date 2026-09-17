import hashlib, json, os, pathlib, subprocess, datetime

PREFERRED=['/generate','/chat','/predict','/respond','/infer','/run']
ROLE=os.environ.get('ROLE','AGENT_RUNTIME_ARCHITECT')
FOCUS=os.environ.get('FOCUS','agent runtime evidence and control')
MODEL=os.environ.get('MODEL','huggingface-projects/llama-3.2-3B-Instruct')
OUT=pathlib.Path('out')
OUT.mkdir(exist_ok=True)

def run(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def payload_for(spec, prompt):
    p={}; set_prompt=False
    for x in spec.get('parameters',[]):
        n=x.get('name') or x.get('parameter_name') or ''
        l=n.lower(); req=bool(x.get('required',False)); default=x.get('default')
        typ=(x.get('type') or {}).get('type') if isinstance(x.get('type'),dict) else x.get('type')
        if l in {'message','prompt','text','query','input','instruction','user_message'}:
            p[n]=prompt; set_prompt=True
        elif l in {'chat_history','history','messages'}: p[n]=[]
        elif l in {'max_new_tokens','max_tokens','maximum_new_tokens'}: p[n]=600
        elif l=='temperature': p[n]=0.1
        elif l=='top_p': p[n]=0.9
        elif l=='top_k': p[n]=40
        elif l in {'system','system_prompt'}: p[n]='REALITY>COHERENCE. CLAIM<=EVIDENCE. WORKER!=AGENT IF NO MODEL CALL. EXECUTION PROOF REQUIRED. UNKNOWN REMAINS UNKNOWN.'
        elif req and default is None:
            if typ=='string' and not set_prompt:
                p[n]=prompt; set_prompt=True
            else:
                return None
    return p if set_prompt else None

def endpoints_from(api):
    if isinstance(api,dict):
        for key in ('named_endpoints','endpoints','api'):
            v=api.get(key)
            if isinstance(v,dict): return list(v.items())
        return list(api.items())
    return []

def extract(raw):
    raw=raw.strip()
    try:
        o=json.loads(raw)
        if isinstance(o,dict):
            for k in ('Response','response','text','output','message'):
                if isinstance(o.get(k),str): return o[k].strip()
    except Exception:
        pass
    return raw

def invoke(space,prompt):
    info=run(['hf-gradio','info',space],120)
    if info.returncode!=0:
        return False,'',{'error':(info.stderr or info.stdout)[-4000:]}
    try:
        api=json.loads(info.stdout)
    except Exception as e:
        return False,'',{'error':f'INFO_JSON_ERROR: {e}','raw':info.stdout[-2000:]}
    eps=endpoints_from(api)
    eps.sort(key=lambda kv:(PREFERRED.index(kv[0]) if kv[0] in PREFERRED else 99,kv[0]))
    errors=[]
    for ep,spec in eps:
        if not isinstance(spec,dict): continue
        payload=payload_for(spec,prompt)
        if payload is None: continue
        pred=run(['hf-gradio','predict',space,ep,json.dumps(payload,ensure_ascii=False)],240)
        if pred.returncode==0 and pred.stdout.strip():
            text=extract(pred.stdout)
            if text:
                return True,text,{'endpoint':ep,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        errors.append({'endpoint':ep,'error':(pred.stderr or pred.stdout)[-2000:]})
    return False,'',{'errors':errors}

prompt=f'''You are role {ROLE} in CÉRÉBRON Ω FARM45 Agent Runtime.
Focus: {FOCUS}.
Audit or design a real agent execution runtime. Distinguish worker process from AI agent, heartbeat from success, logs from correctness, and workflow success from verified model inference. Cover lifecycle/state, tool calls, permissions, sandboxing, idempotency, concurrency, timeout/recovery, evidence artifacts, provenance, human-in-the-loop and kill switch. Do not fabricate executions or evidence. Mark unknowns explicitly. Return concise structured findings with CLAIM<=EVIDENCE.'''

ok,text,meta=invoke(MODEL,prompt)
result={
  'farm':45,'role':ROLE,'focus':FOCUS,'model':MODEL,'provider':'huggingface_space_via_hf_gradio',
  'inference_success':bool(ok),
  'status':'UNREVIEWED_EXTERNAL_AGENT_OUTPUT' if ok else 'EXTERNAL_INFERENCE_FAILED',
  'api_name':meta.get('endpoint') if isinstance(meta,dict) else None,
  'output':text if ok else '',
  'error':None if ok else meta,
  'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'output_sha256':hashlib.sha256(text.encode()).hexdigest() if ok and text else None
}
path=OUT/f'{ROLE}.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
