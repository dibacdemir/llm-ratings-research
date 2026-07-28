import csv, glob, re, os, json, statistics, html, sys
from collections import defaultdict, Counter
csv.field_size_limit(10**7)
OUT=sys.argv[1] if len(sys.argv)>1 else "MOUT"
DRY = "--dry" in sys.argv

files=glob.glob("MTURK_export/*/*.csv")
tag=re.compile(r'<[^>]+>'); ws=re.compile(r'\s+')
def clean(t):
    t=html.unescape(t or ""); t=tag.sub(' ',t); return ws.sub(' ',t).strip()
def slug(s):
    return (re.sub(r'[^A-Za-z0-9]+','_',s).strip('_').lower()[:70]) or "exp"
num_re=re.compile(r'^\s*(-?\d+(?:\.\d+)?)\s*$')
def as_num(s):
    m=num_re.match(s or ""); return float(m.group(1)) if m else None

def fam_index(cols):
    fam=defaultdict(dict)
    for c in cols:
        m=re.match(r'Input\.(.+?)_?(\d+)$', c)
        if m: fam[m.group(1)][int(m.group(2))]=c
    return fam

# group files by experiment folder
byfolder=defaultdict(list)
for f in files: byfolder[f.split('/')[-2]].append(f)

results={}  # folder -> {sentence: [ratings]}
folder_meta={}
for folder, flist in byfolder.items():
    agg=defaultdict(list)
    qmark_debug=[]
    used_files=0
    dims=Counter()
    obs_vals=[]
    for f in flist:
        try:
            rows=list(csv.DictReader(open(f,errors='ignore')))
        except: continue
        if not rows: continue
        cols=rows[0].keys()
        ridx={int(m.group(1)):c for c in cols if (m:=re.match(r'Answer\.Rating(\d+)$',c))}
        if not ridx: continue
        fam=fam_index(cols)
        # candidate stimulus families: index set == rating index set
        R=set(ridx)
        cands=[p for p,d in fam.items() if set(d)==R]
        if not cands:
            cands=[p for p,d in fam.items() if R<=set(d)]
        if not cands: continue
        # score: prefer fewest '?'-ending values (statements, not questions); prefer sentence-y prefixes
        def score(p):
            vals=[clean(rows[0].get(fam[p][i],"")) for i in list(R)[:20]]
            vals=[v for v in vals if v]
            qfrac=sum(v.endswith('?') for v in vals)/max(1,len(vals))
            pref_bonus = -0.5 if re.match(r'(?i)(trial|sent)',p) else 0
            return qfrac+pref_bonus
        stim_p=min(cands,key=score)
        cfam=fam.get('context') or fam.get('context1-')
        used_files+=1
        for r in rows:
            for i,ans_c in ridx.items():
                v=as_num(r.get(ans_c,""))
                if v is None: continue
                scol=fam[stim_p].get(i)
                if not scol: continue
                sent=clean(r.get(scol,""))
                if not sent: continue
                if cfam and cfam.get(i):
                    ctx=clean(r.get(cfam[i],""))
                    if ctx: sent=ctx+" "+sent
                agg[sent].append(v); obs_vals.append(v)
    if not agg or used_files==0: continue
    results[folder]=agg
    lo=min(obs_vals); hi=max(obs_vals)
    # infer dimension from folder name
    fn=folder.lower()
    dim=("naturalness" if 'natural' in fn else "acceptability" if 'accept' in fn else
         "plausibility" if 'plausib' in fn else "rating")
    folder_meta[folder]=dict(scale_lo=lo,scale_hi=hi,dim=dim,nfiles=used_files)

print(f"experiment folders with convertible Rating data: {len(results)}")
tot_sent=sum(len(a) for a in results.values())
tot_rat=sum(sum(len(v) for v in a.values()) for a in results.values())
print(f"total unique sentences: {tot_sent}")
print(f"total individual ratings: {tot_rat}")

if DRY:
    # show 5 examples
    for folder in list(results)[:5]:
        a=results[folder]; m=folder_meta[folder]
        ex=next(iter(a.items()))
        print("="*70); print("FOLDER:",folder[:55])
        print(f"  files={m['nfiles']} sentences={len(a)} scale~{int(m['scale_lo'])}-{int(m['scale_hi'])} dim={m['dim']}")
        print(f"  ex unit: {ex[0][:80]!r}")
        print(f"  ex ratings(n={len(ex[1])}): {ex[1][:15]}")
    sys.exit(0)

# write output
for sub in ["norm_datasets","instructions","_needs_review/norm_datasets","_needs_review/instructions"]:
    os.makedirs(f"{OUT}/{sub}",exist_ok=True)
idx=[]; made=Counter()
for folder,a in results.items():
    m=folder_meta[folder]
    name=slug(folder)
    if made[name]: name=f"{name}_{made[name]+1}"
    made[slug(folder)]+=1
    us=list(a.keys()); qf=sum(u.endswith('?') for u in us)/len(us)
    review = qf>0.3
    od = f"{OUT}/_needs_review" if review else OUT
    with open(f"{od}/norm_datasets/{name}.csv","w",newline='') as fo:
        w=csv.writer(fo); w.writerow(["unit","mean","std","n","individual_ratings"])
        for u in sorted(a):
            r=a[u]; sd=round(statistics.pstdev(r),4) if len(r)>1 else ""
            w.writerow([u,round(statistics.mean(r),4),sd,len(r),
                        json.dumps([int(v) if v==int(v) else v for v in r])])
    q={"naturalness":"How natural does the sentence sound?",
       "acceptability":"How acceptable is the sentence?",
       "plausibility":"How plausible is the sentence?",
       "rating":"Rate the sentence."}[m['dim']]
    lines=[q,
           f"Rate on a scale from {int(m['scale_lo'])} to {int(m['scale_hi'])}. (scale inferred from observed responses)",
           "Answer with one number.","","<<{sentence}>>"]
    open(f"{od}/instructions/{name}_i.txt","w").write("\n".join(lines)+"\n")
    ns=[len(v) for v in a.values()]
    idx.append(dict(file=name,needs_review=int(review),source_folder=folder,dim=m['dim'],
        scale_inferred=f"{int(m['scale_lo'])}-{int(m['scale_hi'])}",n_batch_files=m['nfiles'],
        n_units=len(a),n_ratings=sum(ns),median_n_per_unit=int(statistics.median(ns))))
idx.sort(key=lambda r:-r['n_ratings'])
with open(f"{OUT}/a_index.csv","w",newline='') as fo:
    w=csv.DictWriter(fo,fieldnames=list(idx[0].keys())); w.writeheader(); [w.writerow(r) for r in idx]
print(f"wrote {len(idx)} experiment norm files to {OUT}/")
