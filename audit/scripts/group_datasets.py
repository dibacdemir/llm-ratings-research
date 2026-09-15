"""Deterministic grouping of mturk_norms / surveyor_norms datasets.

Levels
  E (experiment): batches / Latin-square lists / waves / re-runs of ONE experiment
  P (project)   : different experiments of ONE study (e.g. same stimuli rated on
                  another dimension, or another experiment under the same project name)
Rules (mechanical; no curation, no LLM):
  E  <- stimulus containment >= 0.8 (shared/min(|A|,|B|)) AND same dimension AND same scale
     <- OR same project token AND same dimension AND same scale AND the names differ only
        by a list/set/wave/version/rerun/date suffix (Latin-square lists are disjoint by design)
  P  <- everything in the same E
     <- OR containment >= 0.8 with a DIFFERENT dimension (same stimuli, another rating)
     <- OR same project token (first non-generic token of the dataset name; surveyor
        additionally requires the same owner account)
  Weak stimulus overlap (containment 0.2-0.8) is REPORTED as evidence, never used to merge
  (labs reuse filler sentences across unrelated studies).
Confidence: high = stimulus evidence; medium = name-token/suffix only; singleton = none.
Usage: python audit/scripts/group_datasets.py <RAW_MTURK_DIR>   (writes audit/dataset_grouping.csv)
"""
import csv, glob, os, re, sys, itertools
from collections import defaultdict
RAW_MTURK = sys.argv[1] if len(sys.argv) > 1 else None
MONTHS = r'jan|feb|mar|march|apr|april|may|june|jul|july|aug|sept|sep|oct|nov|dec'
GENERIC = {'sentence','sentences','naturalness','survey','for','with','a','and','the','of','items','item','code','plus','rating','ratings','question','questions','comprehension','short','texts','two','study','test','norming','expt','exp','project','acceptability','judgments','copy','version','main','final','extension','replication','rerunning','update','likert','set','list','english','in','syntax','semantics','task','tasks','language','response','survey','data','v','ratings'}
SUFFIX = re.compile(r'(?:^|_)(v\d+|v\d+o\d+|list\d+|set\d+[ab]?|end(?:_\d+)?|rep\d*|rerunning(?:_\d+)?|\d+[ab]?|(?:%s)(?:_\d+)?|(?:19|20)\d\d|expt?_?\d+|e\d+|declaratives|items|main|final|update\d*)(?=_|$)' % MONTHS)
def norm_unit(u): return re.sub(r'[^a-z0-9一-鿿Ѐ-ӿ]+', '', u.lower())
def cont(a, b): return len(a & b) / min(len(a), len(b)) if a and b else 0.0
def tokens(name):
    n = re.sub(r'(survey_)?code_[a-z_]+$', '', name.lower())
    return [t for t in n.split('_') if t]
def project_token(name):
    ts = [t for t in tokens(name) if t not in GENERIC and not re.fullmatch(r'\d+|v\d+|v\d+o\d+|list\d+|set\d+[ab]?|end|rep\d*|e\d+|expt?|(%s)' % MONTHS, t)]
    return ts[0] if ts else name
def core(name):
    """name with all list/wave/version/date suffix tokens removed -> identity of the experiment series"""
    n = name.lower()
    n = re.sub(r'(survey_)?code_[a-z_]+$', '', n)
    prev = None
    while prev != n:
        prev = n; n = SUFFIX.sub('', n)
    return n.strip('_')
class UF:
    def __init__(s): s.p = {}
    def f(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x: s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x
    def u(s, a, b): s.p[s.f(a)] = s.f(b)
def read_units(p):
    with open(p, encoding='utf-8') as fh: return {norm_unit(r['unit']) for r in csv.DictReader(fh)}

def run(collection, items):
    """items: list of dict(name, units, dim, scale, owner, dates, extra)"""
    E, P, ev, weak = UF(), UF(), defaultdict(list), defaultdict(list)
    for a, b in itertools.combinations(items, 2):
        c = cont(a['units'], b['units']); same_dim = a['dim'] == b['dim']; same_scale = a['scale'] == b['scale']
        same_tok = a['tok'] == b['tok'] and (collection == 'mturk' or a['owner'] == b['owner'])
        if c >= 0.8 and same_dim and same_scale:
            E.u(a['name'], b['name']); P.u(a['name'], b['name'])
            ev[a['name']].append(f"same stimuli+dimension as {b['name']} (cont={c:.2f})"); ev[b['name']].append(f"same stimuli+dimension as {a['name']} (cont={c:.2f})")
        elif c >= 0.8:
            P.u(a['name'], b['name'])
            ev[a['name']].append(f"same stimuli, other dimension: {b['name']} (cont={c:.2f})"); ev[b['name']].append(f"same stimuli, other dimension: {a['name']} (cont={c:.2f})")
        elif c >= 0.2:
            weak[a['name']].append(f"{b['name']} ({c:.2f})"); weak[b['name']].append(f"{a['name']} ({c:.2f})")
        if same_tok:
            P.u(a['name'], b['name'])
            if a['core'] == b['core'] and same_dim and same_scale:
                E.u(a['name'], b['name']); ev[a['name']].append(f"series suffix variant of {b['name']}"); ev[b['name']].append(f"series suffix variant of {a['name']}")
            else:
                ev[a['name']].append(f"project token '{a['tok']}' = {b['name']}"); ev[b['name']].append(f"project token '{a['tok']}' = {a['name']}")
    names = [i['name'] for i in items]
    out = []
    for i in items:
        e = ev[i['name']]
        conf = 'high' if any(s.startswith('same stimuli') for s in e) else ('medium (names only)' if e else 'singleton')
        out.append(dict(collection=collection, dataset=i['name'], experiment_group=f"{collection[0].upper()}-E{names.index(E.f(i['name']))}",
                        project_group=f"{collection[0].upper()}-P{names.index(P.f(i['name']))}", project_token=i['tok'], series_core=i['core'],
                        dimension=i['dim'], scale=i['scale'], owner=i['owner'], dates=i['dates'], n_units=len(i['units']),
                        evidence=' | '.join(e[:5]), shares_stimuli_weakly_with=' | '.join(weak[i['name']][:4]), confidence=conf, ask_collaborator='yes' if conf != 'high' else 'no'))
    return out

rows = []
# ---- MTurk
items = []
for r in csv.DictReader(open('mturk_norms/a_index.csv')):
    f = r['file']; p = f'mturk_norms/norm_datasets/{f}.csv'
    if not os.path.exists(p): p = f'mturk_norms/non_english/norm_datasets/{f}.csv'
    dates = set()
    if RAW_MTURK:
        for b in glob.glob(f"{RAW_MTURK}/{r['source_folder']}/*.csv"):
            m = re.search(r'(\d{4}-\d{2}-\d{2})_Batch', os.path.basename(b))
            if m: dates.add(m.group(1))
    items.append(dict(name=f, units=read_units(p), dim=r.get('dimension',''), scale=r.get('scale_labels','') or r.get('scale',''), owner='',
                      dates=(min(dates) + '..' + max(dates)) if dates else '', tok=project_token(f), core=core(f)))
rows += run('mturk', items)
# ---- Surveyor
items = []
for r in csv.DictReader(open('surveyor_norms/a_index.csv')):
    f, d = r['file'], r['domain']; p = f'surveyor_norms/norm_datasets/{d}/{f}.csv'
    if not os.path.exists(p): p = f'surveyor_norms/non_english/norm_datasets/{d}/{f}.csv'
    ts = re.search(r'_y(\d{4})m(\d{2})d(\d{2})', r['survey_id'])
    items.append(dict(name=f, units=read_units(p), dim=re.sub(r'\s+', ' ', (r.get('prompt') or '').strip().lower()), scale=(r.get('scale') or '').strip(),
                      owner=r['user'], dates='-'.join(ts.groups()) if ts else '', tok=project_token(f), core=core(f)))
rows += run('surveyor', items)
with open('audit/dataset_grouping.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for col in ('mturk', 'surveyor'):
    rs = [r for r in rows if r['collection'] == col]
    eg, pg = defaultdict(list), defaultdict(list)
    for r in rs: eg[r['experiment_group']].append(r['dataset']); pg[r['project_group']].append(r['dataset'])
    print(f"{col}: {len(rs)} datasets -> {len(eg)} experiments ({sum(len(v)>1 for v in eg.values())} multi), {len(pg)} projects ({sum(len(v)>1 for v in pg.values())} multi); high={sum(r['confidence']=='high' for r in rs)} medium={sum(r['confidence'].startswith('medium') for r in rs)} singleton={sum(r['confidence']=='singleton' for r in rs)}")
