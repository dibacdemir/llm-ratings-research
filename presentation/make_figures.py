import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
csv.field_size_limit(10**7)
HERE=os.path.dirname(os.path.abspath(__file__))

plt.rcParams.update({
    "font.family":"DejaVu Sans","font.size":11,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.edgecolor":"#5b655f","axes.labelcolor":"#182220","text.color":"#182220",
    "xtick.color":"#5b655f","ytick.color":"#5b655f","figure.facecolor":"white","savefig.facecolor":"white",
})

DOM_ORDER=["Form (sub-lexical)","Lexical: affective","Lexical: perceptual/motor",
           "Lexical: conceptual","Syntax","Sentence semantics"]
COL={"Form (sub-lexical)":"#CC79A7","Lexical: affective":"#08519C",
     "Lexical: perceptual/motor":"#4A90C2","Lexical: conceptual":"#9CC9E3",
     "Syntax":"#D55E00","Sentence semantics":"#009E73"}
SHORT={"Form (sub-lexical)":"Form\n(sub-lexical)","Lexical: affective":"Lexical:\naffective",
       "Lexical: perceptual/motor":"Lexical:\nperceptual/motor","Lexical: conceptual":"Lexical:\nconceptual",
       "Syntax":"Syntax","Sentence semantics":"Sentence\nsemantics"}

cat=list(csv.DictReader(open(f"{HERE}/dataset_catalog.csv")))
for r in cat:
    r['n_items']=int(r['n_items']); r['n_ratings']=int(r['n_ratings'])
    r['r']=float(r['split_half_r']) if r['split_half_r'] not in ('','None') else None

def dstats(d):
    rs=[r for r in cat if r['domain']==d]
    return len(rs), sum(x['n_items'] for x in rs), sum(x['n_ratings'] for x in rs)

# ============ FIG 1: coverage tiny-bars ============
HDR={"Form (sub-lexical)":"Form","Lexical: affective":"Affective",
     "Lexical: perceptual/motor":"Perceptual /\nmotor","Lexical: conceptual":"Conceptual",
     "Syntax":"Syntax","Sentence semantics":"Sentence\nsemantics"}
LBLCOL=dict(COL); LBLCOL["Lexical: conceptual"]="#3a7fb0"  # readable light-blue label
tasks=[]
for d in DOM_ORDER:
    grp=sorted([r for r in cat if r['domain']==d], key=lambda x:-x['n_items'])
    tasks.append((d,grp))
fig,ax=plt.subplots(figsize=(17,6.6))
xt=ax.get_xaxis_transform()  # (data-x, axes-y)
x=0; gap=7; spans={}
for d,grp in tasks:
    xs=np.arange(x,x+len(grp))
    ax.bar(xs,[g['n_items'] for g in grp],width=0.92,color=COL[d],edgecolor="white",linewidth=0.15,zorder=3)
    ax.axvspan(x-0.7,x+len(grp)-0.3,color=COL[d],alpha=0.05,zorder=0)
    cx=x+len(grp)/2-0.5; spans[d]=(x-0.7,x+len(grp)-0.3,cx)
    ntask=dstats(d)[0]
    ax.text(cx,1.045,HDR[d],transform=xt,ha="center",va="bottom",fontsize=10.5,weight="bold",
            color=LBLCOL[d],linespacing=0.95,clip_on=False)
    ax.text(cx,1.018,f"{ntask} tasks",transform=xt,ha="center",va="bottom",fontsize=8.5,color="#5b655f",clip_on=False)
    x+=len(grp)+gap
# hierarchical bracket over the three blue "Lexical" groups
lx0=spans["Lexical: affective"][0]; lx1=spans["Lexical: conceptual"][1]
lcx=(lx0+lx1)/2
ax.plot([lx0,lx1],[1.135,1.135],transform=xt,color="#4A90C2",lw=1.4,clip_on=False)
for xx in (lx0,lx1): ax.plot([xx,xx],[1.125,1.135],transform=xt,color="#4A90C2",lw=1.4,clip_on=False)
ax.text(lcx,1.15,"LEXICAL  ·  word meaning",transform=xt,ha="center",va="bottom",
        fontsize=9.5,weight="bold",color="#2f6ea0",clip_on=False)
ax.set_yscale("log"); ax.set_ylim(55,60000)
ax.set_xlim(-3,x-gap+1)
ax.set_ylabel("Number of items  (words / sentences)",fontsize=11.5)
ax.set_xticks([])
ax.set_xlabel("335 rating tasks  ·  each bar = one task / property, ordered by size within its domain",fontsize=10.5)
ax.set_title("Coverage across six levels of linguistic analysis",fontsize=15,weight="bold",loc="left",y=1.26)
ax.grid(axis="y",color="#e0e4de",linewidth=0.7,zorder=0); ax.set_axisbelow(True)
ax.spines["left"].set_color("#c9cec7")
fig.subplots_adjust(top=0.74)
fig.savefig(f"{HERE}/fig1_coverage.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig1_coverage.pdf",bbox_inches="tight")
plt.close(fig)

# ============ FIG 2: split-half reliability by domain ============
fig,ax=plt.subplots(figsize=(9,5.4))
rng=np.random.default_rng(1)
allr=[]
for i,d in enumerate(DOM_ORDER):
    rs=[r['r'] for r in cat if r['domain']==d and r['r'] is not None]
    allr+=rs
    y=i+rng.uniform(-0.16,0.16,len(rs))
    ax.scatter(rs,y,s=22,color=COL[d],alpha=0.8,edgecolor="white",linewidth=0.4,zorder=3)
    if rs:
        med=np.median(rs)
        ax.plot([med,med],[i-0.32,i+0.32],color="#182220",lw=2,zorder=4)
        ax.text(1.005,i,f"n={len(rs)}  med={med:.2f}",va="center",fontsize=9,color="#5b655f")
om=np.median(allr)
ax.axvline(om,color="#9aa39a",ls="--",lw=1,zorder=1)
ax.text(om,-0.7,f"overall median r = {om:.2f}",ha="center",va="bottom",fontsize=9.5,color="#5b655f")
ax.set_yticks(range(6)); ax.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER])
ax.set_ylim(5.6,-1.0)   # inverted, extra headroom for the median label
ax.set_xlim(0.45,1.0); ax.set_xlabel("Split-half reliability (Spearman–Brown corrected)",fontsize=11.5)
ax.set_title("Human ratings are highly reliable where individual responses exist",
             fontsize=13,weight="bold",loc="left",y=1.10)
ax.text(0,1.02,f"{len(allr)} of 335 tasks have item-level individual ratings (median r = {om:.2f})",
        transform=ax.transAxes,fontsize=9.5,color="#5b655f")
ax.grid(axis="x",color="#e0e4de",lw=0.7); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{HERE}/fig2_reliability.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig2_reliability.pdf",bbox_inches="tight")
plt.close(fig)

# ============ FIG 3: domain coverage summary ============
fig,(a1,a2)=plt.subplots(1,2,figsize=(13,4.6),gridspec_kw={"width_ratios":[1,1.15]})
ys=np.arange(6)[::-1]
tvals=[dstats(d)[0] for d in DOM_ORDER]; ivals=[dstats(d)[1] for d in DOM_ORDER]
cols=[COL[d] for d in DOM_ORDER]
a1.barh(ys,tvals,color=cols,edgecolor="white")
for y,v in zip(ys,tvals): a1.text(v+2,y,str(v),va="center",fontsize=10,color="#182220")
a1.set_yticks(ys); a1.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER],fontsize=10)
a1.set_xlabel("# rating tasks"); a1.set_title("Tasks per domain",fontsize=12,weight="bold",loc="left")
a1.set_xlim(0,max(tvals)*1.18); a1.grid(axis="x",color="#e0e4de",lw=0.7); a1.set_axisbelow(True)
a2.barh(ys,ivals,color=cols,edgecolor="white")
a2.set_xscale("log")
for y,v,d in zip(ys,ivals,DOM_ORDER):
    _,_,nrt=dstats(d); a2.text(v*1.15,y,f"{v:,} items",va="center",fontsize=9,color="#182220")
a2.set_yticks([]); a2.set_xlabel("# items (log scale)"); a2.set_title("Items per domain",fontsize=12,weight="bold",loc="left")
a2.set_xlim(400,2_000_000); a2.grid(axis="x",color="#e0e4de",lw=0.7); a2.set_axisbelow(True)
fig.suptitle("Dataset composition by linguistic domain",fontsize=14,weight="bold",x=0.02,ha="left",y=1.02)
fig.tight_layout()
fig.savefig(f"{HERE}/fig3_domains.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig3_domains.pdf",bbox_inches="tight")
plt.close(fig)

# headline numbers
T=len(cat); I=sum(r['n_items'] for r in cat); R=sum(r['n_ratings'] for r in cat)
nind=sum(1 for r in cat if r['r'] is not None)
print(f"tasks={T} items={I:,} ratings={R:,} reliab_tasks={nind} median_r={np.median(allr):.3f}")
print("figures written: fig1_coverage, fig2_reliability, fig3_domains (png+pdf)")
