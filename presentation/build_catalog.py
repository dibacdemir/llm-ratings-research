import csv, glob, os, json, re
import numpy as np
csv.field_size_limit(10**7)
REPO=os.path.dirname(os.path.abspath(__file__))+"/.."

# ---------- domain taxonomy (Level-1 domain, Level-2 subdomain) ----------
# keyword -> (domain, subdomain). First match wins; order = priority.
RULES = [
    # Sentence-level semantics / pragmatics / discourse  (check before syntax)
    (r'plausib|predictab|comprehensib|sensib|\bsense\b|coheren|connected|\bcause\b|causal|discourse|inference|literal|meaning|implausible', ("Sentence semantics","Plausibility / coherence / discourse")),
    # Syntax (well-formedness judgments)
    (r'grammatical|grammaticality|well formed|acceptab|naturaln|naturalness', ("Syntax","Acceptability / naturalness")),
    # Form: orthography-phonology / sound-symbolism
    (r'spelling|pronunciation|transparency|orthograph|phonolog', ("Form (sub-lexical)","Orthography–phonology")),
    (r'iconicity', ("Form (sub-lexical)","Sound–meaning (iconicity)")),
    (r'pseudoword', ("Form (sub-lexical)","Pseudoword")),
    # Lexical: affective
    (r'valence|arousal|dominance|emotion|polarity|morality|\bmoral\b|motivation|affect', ("Lexical: affective","Affective")),
    # Lexical: perceptual / motor
    (r'auditory|visual|haptic|gustatory|olfactory|interocept|tactile|taste|smell|colou?r|\bsound\b|hand arm|foot leg|\bhead\b|mouth|torso|motion|sensorimotor|body object|\bspace\b|spatial', ("Lexical: perceptual/motor","Sensorimotor")),
    (r'imageab|imaginab|concrete|\bsize\b', ("Lexical: perceptual/motor","Imageability / concreteness / size")),
    # Lexical: conceptual / other
    (r'age of acquisition|\baoa\b|acquisition', ("Lexical: conceptual","Age of acquisition")),
    (r'frequency', ("Lexical: conceptual","Frequency")),
    (r'familiar', ("Lexical: conceptual","Familiarity")),
    (r'socialness|social interaction|\bsocial\b', ("Lexical: conceptual","Social")),
    (r'gender', ("Lexical: conceptual","Gender")),
    (r'cognition|mental states|thought|physical objects|places|quantity|\btime\b|semantic', ("Lexical: conceptual","Conceptual / semantic")),
]
def classify(descriptor, source):
    d=re.sub(r'[^a-z0-9]+',' ',descriptor.lower())  # underscores/punct -> spaces so \b works
    for pat,(dom,sub) in RULES:
        if re.search(pat,d): return dom,sub
    # source-aware default: the surveyor/mturk sentence corpora are naturalness/acceptability
    if source in ("surveyor","mturk"): return ("Syntax","Acceptability / naturalness")
    return ("Other / unspecified","Unspecified")

# ---------- split-half reliability (item-level, Spearman-Brown) ----------
rng=np.random.default_rng(0)
def split_half(csvpath, max_items=6000):
    per=[]  # list of arrays of ratings per item
    with open(csvpath,encoding='utf-8',errors='ignore') as fh:
        rd=csv.DictReader(fh)
        for row in rd:
            v=row.get('individual_ratings','')
            if not v or v.strip() in ('','[]'): continue
            try: arr=json.loads(v)
            except: continue
            arr=[x for x in arr if isinstance(x,(int,float))]
            if len(arr)>=4: per.append(np.array(arr,dtype=float))
    if len(per)<10: return None,0
    if len(per)>max_items:
        idx=rng.choice(len(per),max_items,replace=False); per=[per[i] for i in idx]
    h1=[];h2=[]
    for a in per:
        a=a.copy(); rng.shuffle(a); m=len(a)//2
        h1.append(a[:m].mean()); h2.append(a[m:2*m].mean())
    h1=np.array(h1);h2=np.array(h2)
    if h1.std()<1e-9 or h2.std()<1e-9: return None,len(per)
    r=np.corrcoef(h1,h2)[0,1]
    sb=2*r/(1+r) if (1+r)!=0 else r   # Spearman-Brown
    return round(float(sb),3), len(per)

# ---------- descriptor per source ----------
def published_desc(name): return name  # study_property
sv_idx={r['file']:r for r in csv.DictReader(open(f"{REPO}/surveyor_norms/a_index.csv"))}
mt_idx={r['file']:r for r in csv.DictReader(open(f"{REPO}/mturk_norms/a_index.csv"))}

def scan(path, source):
    out=[]
    for f in sorted(glob.glob(f"{path}/*.csv")):
        base=os.path.basename(f)[:-4]
        rows=list(csv.DictReader(open(f,encoding='utf-8',errors='ignore')))
        if not rows or 'unit' not in rows[0]: continue
        n_items=len(rows)
        try: n_ratings=sum(int(x['n']) for x in rows if x.get('n','').strip().isdigit())
        except: n_ratings=0
        if source=="published":
            study=base.split('_')[0]; desc=base
        elif source=="surveyor":
            r=sv_idx.get(base,{}); study="surveyor"; desc=f"{r.get('critical_type','')} {base} {r.get('prompt','')}"
        else:
            r=mt_idx.get(base,{}); study="mturk"; desc=f"{r.get('dim','')} {r.get('source_folder','')} {base}"
        dom,sub=classify(desc,source)
        sh, n_rel=split_half(f)
        out.append(dict(source=source,study=study,task=base,domain=dom,subdomain=sub,
                        n_items=n_items,n_ratings=n_ratings,
                        has_individual=int(sh is not None or n_rel>0),
                        split_half_r=(sh if sh is not None else "")))
    return out

cat=[]
for d in sorted(glob.glob(f"{REPO}/norm_datasets/*_data")): cat+=scan(d,"published")
cat+=scan(f"{REPO}/surveyor_norms/norm_datasets","surveyor")
cat+=scan(f"{REPO}/mturk_norms/norm_datasets","mturk")

with open(f"{REPO}/presentation/dataset_catalog.csv","w",newline='') as fo:
    w=csv.DictWriter(fo,fieldnames=list(cat[0].keys())); w.writeheader()
    for r in cat: w.writerow(r)

# summary
from collections import Counter, defaultdict
print("tasks:",len(cat))
print("total items:",sum(r['n_items'] for r in cat))
print("total ratings:",sum(r['n_ratings'] for r in cat))
byd=defaultdict(lambda:[0,0,0])
for r in cat:
    byd[r['domain']][0]+=1; byd[r['domain']][1]+=r['n_items']; byd[r['domain']][2]+=r['n_ratings']
print("\n=== by domain (tasks / items / ratings):")
for dom,(t,i,rt) in sorted(byd.items(),key=lambda x:-x[1][1]):
    print(f"  {dom:28s} {t:4d} tasks  {i:9,d} items  {rt:12,d} ratings")
rels=[r['split_half_r'] for r in cat if r['split_half_r']!=""]
print(f"\nsplit-half computed for {len(rels)} tasks; median r = {np.median([float(x) for x in rels]):.3f}")
