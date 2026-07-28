import csv, os, json, re, sys, statistics, html
from collections import defaultdict, Counter

ROOT="surveyor_export"; OUT=sys.argv[1]
for sub in ["norm_datasets","instructions","_needs_review/norm_datasets","_needs_review/instructions"]:
    os.makedirs(f"{OUT}/{sub}", exist_ok=True)

prof=json.load(open("profile.json"))
conv=[x for x in prof if x['frac_num']>0.9 and not x['has_audio'] and not x['has_img']]
num_re=re.compile(r'^\s*(-?\d+(?:\.\d+)?)')
def as_num(s):
    m=num_re.match(s or ""); return float(m.group(1)) if m else None
tag_re=re.compile(r'<[^>]+>'); ws_re=re.compile(r'\s+')
def clean(t):
    t=html.unescape(t or ""); t=tag_re.sub(' ',t); return ws_re.sub(' ',t).strip()
def base(sid): return os.path.basename(sid)
def rd(f):
    r=csv.reader(open(f,errors='ignore')); hdr=[h.lstrip('﻿') for h in next(r)]
    return [dict(zip(hdr,row)) for row in r]
def slug(s):
    s=re.sub(r'_y20\d\dm\d\dd\d\dh\d\dm\d\d.*$','',s)
    return (re.sub(r'[^A-Za-z0-9]+','_',s).strip('_').lower()[:60]) or "survey"

idx=[]; made=Counter()
for x in conv:
    user=x['user']; sid=x['sid']; d=f"{ROOT}/{user}/{sid}"; b=base(sid)
    dr=rd(f"{d}/{b}_data.csv"); sr=rd(f"{d}/{b}_stimuli.csv")
    stim={(r['experiment'],str(r['item']),r['condition']):r for r in sr}
    agg=defaultdict(list); po=Counter()
    for r in dr:
        v=as_num(r.get('response','')); 
        if v is None: continue
        s=stim.get((r['experiment'],str(r['item']),r['cond']))
        if not s: continue
        unit=clean(s.get('sentence',''))
        if not unit: continue
        agg[unit].append(v); po[(clean(s.get('prompt','')),s.get('options',''))]+=1
    if not agg: continue
    (prompt,options),_=po.most_common(1)[0]
    opts=[o for o in (options or "").split('_') if o.strip()]
    scale=f"Rate on a scale from {opts[0].strip()} to {opts[-1].strip()}." if opts and as_num(opts[0]) is not None and as_num(opts[-1]) is not None else ""
    name=slug(sid)
    if made[name]: name=f"{name}_{made[name]+1}"
    made[slug(sid)]+=1
    review = not prompt.strip()   # empty prompt => attitude questionnaire, needs human review
    ndir = f"{OUT}/_needs_review" if review else OUT
    with open(f"{ndir}/norm_datasets/{name}.csv",'w',newline='') as f:
        w=csv.writer(f); w.writerow(["unit","mean","std","n","individual_ratings"])
        for u in sorted(agg):
            r=agg[u]; sd=round(statistics.pstdev(r),4) if len(r)>1 else ""
            w.writerow([u, round(statistics.mean(r),4), sd, len(r),
                        json.dumps([int(v) if v==int(v) else v for v in r])])
    lines=([prompt] if prompt else [])+([scale] if scale else [])+["Answer with one number.","","<<{sentence}>>"]
    open(f"{ndir}/instructions/{name}_i.txt","w").write("\n".join(lines)+"\n")
    ns=[len(v) for v in agg.values()]
    idx.append(dict(file=name, needs_review=int(review), critical_type=x['ctype'],
        user=user, survey_id=re.sub(r'_y20.*$','',sid), participants=int(x['parts']),
        n_units=len(agg), n_ratings=sum(ns), median_n_per_unit=int(statistics.median(ns)),
        scale=(f"{opts[0].strip()}  ..  {opts[-1].strip()}" if opts else ""), prompt=prompt[:90]))

idx.sort(key=lambda r:(r['needs_review'], -r['participants']))
with open(f"{OUT}/a_index.csv",'w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=list(idx[0].keys())); w.writeheader(); [w.writerow(r) for r in idx]
clean_n=sum(1 for r in idx if not r['needs_review'])
print(f"clean surveys: {clean_n} | needs_review: {len(idx)-clean_n}")
print("clean units:", sum(r['n_units'] for r in idx if not r['needs_review']),
      "| clean ratings:", sum(r['n_ratings'] for r in idx if not r['needs_review']))
from collections import Counter as C
print("clean by type:", dict(C(r['critical_type'] for r in idx if not r['needs_review'])))
print("median_n_per_unit distribution (clean):", sorted(C(r['median_n_per_unit'] for r in idx if not r['needs_review']).items()))
