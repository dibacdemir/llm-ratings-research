import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
csv.field_size_limit(10**7)
HERE=os.path.dirname(os.path.abspath(__file__))

# ---- Nature-ish global style ----
SANS = "Helvetica" if "Helvetica" in {f.name for f in fm.fontManager.ttflist} else "Arial"
INK="#1a1a1a"; MUT="#6b6b6b"; AX="#8a8a8a"; GRID="#ecedea"
plt.rcParams.update({
    "font.family":SANS,"font.size":11,"pdf.fonttype":42,"ps.fonttype":42,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.linewidth":0.8,"axes.edgecolor":AX,
    "axes.labelcolor":INK,"axes.titlecolor":INK,"text.color":INK,
    "xtick.color":AX,"ytick.color":AX,"xtick.labelcolor":MUT,"ytick.labelcolor":MUT,
    "xtick.major.width":0.8,"ytick.major.width":0.8,"xtick.major.size":3.5,"ytick.major.size":3.5,
    "xtick.direction":"out","ytick.direction":"out",
    "figure.facecolor":"white","savefig.facecolor":"white","axes.titlepad":10,
})

DOM_ORDER=["Form (sub-lexical)","Lexical: affective","Lexical: perceptual/motor",
           "Lexical: conceptual","Syntax","Sentence semantics"]
COL={"Form (sub-lexical)":"#C1699B","Lexical: affective":"#12507F",
     "Lexical: perceptual/motor":"#4A90C2","Lexical: conceptual":"#9EC9E2",
     "Syntax":"#D8622A","Sentence semantics":"#159C7B"}
LBLCOL=dict(COL); LBLCOL["Lexical: conceptual"]="#4a92c0"

cat=list(csv.DictReader(open(f"{HERE}/dataset_catalog.csv")))
for r in cat:
    r['n_items']=int(r['n_items']); r['n_ratings']=int(r['n_ratings'])
    r['r']=float(r['split_half_r']) if r['split_half_r'] not in ('','None') else None
def dstats(d):
    rs=[r for r in cat if r['domain']==d]; return len(rs),sum(x['n_items'] for x in rs),sum(x['n_ratings'] for x in rs)

def finish(ax):
    ax.tick_params(length=3.5)
    for s in ax.spines.values(): s.set_color(AX)

# ============ FIG 1: coverage tiny-bars ============
HDR={"Form (sub-lexical)":"Form","Lexical: affective":"Affective",
     "Lexical: perceptual/motor":"Perceptual /\nmotor","Lexical: conceptual":"Conceptual",
     "Syntax":"Syntax","Sentence semantics":"Sentence\nsemantics"}
tasks=[(d,sorted([r for r in cat if r['domain']==d],key=lambda x:-x['n_items'])) for d in DOM_ORDER]

fig,ax=plt.subplots(figsize=(16,5.6))
xt=ax.get_xaxis_transform()
x=0; gap=9; spans={}
for d,grp in tasks:
    xs=np.arange(x,x+len(grp))
    ax.bar(xs,[g['n_items'] for g in grp],width=0.86,color=COL[d],linewidth=0,zorder=3)
    x0,x1,cx=x-0.6,x+len(grp)-0.4,x+len(grp)/2-0.5; spans[d]=(x0,x1,cx)
    # thin colored identity rule just under the baseline
    ax.plot([x0,x1],[-0.012,-0.012],transform=xt,color=COL[d],lw=2.6,solid_capstyle="butt",clip_on=False,zorder=5)
    ax.text(cx,1.05,HDR[d],transform=xt,ha="center",va="bottom",fontsize=11,weight="bold",
            color=LBLCOL[d],linespacing=0.95,clip_on=False)
    ax.text(cx,1.02,f"{dstats(d)[0]} tasks",transform=xt,ha="center",va="bottom",fontsize=8.5,color=MUT,clip_on=False)
    x+=len(grp)+gap
# hierarchical bracket over the three lexical (blue) groups
lx0=spans["Lexical: affective"][0]; lx1=spans["Lexical: conceptual"][1]; lcx=(lx0+lx1)/2
ax.plot([lx0,lx1],[1.15,1.15],transform=xt,color="#7fb0d4",lw=1.1,clip_on=False)
for xx in (lx0,lx1): ax.plot([xx,xx],[1.142,1.15],transform=xt,color="#7fb0d4",lw=1.1,clip_on=False)
ax.text(lcx,1.165,"L E X I C A L   ·   w o r d   m e a n i n g",transform=xt,ha="center",va="bottom",
        fontsize=8.5,weight="bold",color="#5a93bd",clip_on=False)

ax.set_yscale("log"); ax.set_ylim(60,100000); ax.set_xlim(-4,x-gap+2)
ax.set_ylabel("Number of items  (words / sentences)",fontsize=11)
ax.set_xticks([])
ax.set_title("Coverage across six levels of linguistic analysis",fontsize=15,weight="bold",loc="left",y=1.30)
ax.text(0,1.235,"each bar = one of 335 rating tasks · height = number of items · ordered by size within domain",
        transform=ax.transAxes,fontsize=9.5,color=MUT)
ax.grid(axis="y",color=GRID,linewidth=0.8,zorder=0); ax.set_axisbelow(True)
ax.spines["bottom"].set_visible(False)
finish(ax); ax.tick_params(axis="x",length=0)
fig.subplots_adjust(top=0.72,left=0.06,right=0.985,bottom=0.06)
fig.savefig(f"{HERE}/fig1_coverage.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig1_coverage.pdf",bbox_inches="tight")
plt.close(fig)

# ============ FIG 2: split-half reliability ============
fig,ax=plt.subplots(figsize=(8.8,5.0))
rng=np.random.default_rng(1); allr=[]
for i,d in enumerate(DOM_ORDER):
    rs=[r['r'] for r in cat if r['domain']==d and r['r'] is not None]; allr+=rs
    y=i+rng.uniform(-0.15,0.15,len(rs))
    ax.scatter(rs,y,s=16,color=COL[d],alpha=0.75,edgecolor="white",linewidth=0.3,zorder=3)
    if rs:
        med=np.median(rs)
        ax.plot([med,med],[i-0.30,i+0.30],color=INK,lw=1.8,zorder=4,solid_capstyle="round")
        ax.text(1.006,i,f"med {med:.2f}   n={len(rs)}",va="center",fontsize=8.5,color=MUT)
om=np.median(allr)
ax.axvline(om,color="#b9beb6",ls=(0,(4,3)),lw=0.9,zorder=1)
ax.set_yticks(range(6)); ax.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER],fontsize=10.5)
ax.set_ylim(5.6,-0.9); ax.set_xlim(0.45,1.0)
ax.set_xlabel("Split-half reliability  (Spearman–Brown corrected)",fontsize=11)
ax.set_title("Human ratings are highly reliable",fontsize=14,weight="bold",loc="left",y=1.09)
ax.text(0,1.02,f"item-level split-half, 291 of 335 tasks with individual responses · overall median r = {om:.2f}",
        transform=ax.transAxes,fontsize=9,color=MUT)
ax.grid(axis="x",color=GRID,lw=0.8); ax.set_axisbelow(True); finish(ax)
fig.subplots_adjust(top=0.86,left=0.20,right=0.90,bottom=0.12)
fig.savefig(f"{HERE}/fig2_reliability.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig2_reliability.pdf",bbox_inches="tight")
plt.close(fig)

# ============ FIG 3: composition summary ============
fig,(a1,a2)=plt.subplots(1,2,figsize=(12.5,4.3),gridspec_kw={"width_ratios":[1,1.1],"wspace":0.08})
ys=np.arange(6)[::-1]; cols=[COL[d] for d in DOM_ORDER]
tvals=[dstats(d)[0] for d in DOM_ORDER]; ivals=[dstats(d)[1] for d in DOM_ORDER]
a1.barh(ys,tvals,height=0.66,color=cols,linewidth=0)
for y,v in zip(ys,tvals): a1.text(v+3,y,str(v),va="center",fontsize=9.5,color=INK)
a1.set_yticks(ys); a1.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER],fontsize=10)
a1.set_xlabel("Rating tasks",fontsize=10.5); a1.set_title("Tasks per domain",fontsize=12,weight="bold",loc="left")
a1.set_xlim(0,max(tvals)*1.16); a1.grid(axis="x",color=GRID,lw=0.8); a1.set_axisbelow(True); finish(a1)
a2.barh(ys,ivals,height=0.66,color=cols,linewidth=0); a2.set_xscale("log")
for y,v in zip(ys,ivals): a2.text(v*1.18,y,f"{v:,}",va="center",fontsize=9.5,color=INK)
a2.set_yticks([]); a2.set_xlabel("Items  (log scale)",fontsize=10.5)
a2.set_title("Items per domain",fontsize=12,weight="bold",loc="left")
a2.set_xlim(500,3_000_000); a2.grid(axis="x",color=GRID,lw=0.8); a2.set_axisbelow(True); finish(a2)
a2.spines["left"].set_visible(False); a2.tick_params(axis="y",length=0)
fig.suptitle("Dataset composition by linguistic domain",fontsize=13.5,weight="bold",x=0.045,ha="left",y=1.0)
fig.subplots_adjust(top=0.84,left=0.16,right=0.985,bottom=0.13)
fig.savefig(f"{HERE}/fig3_domains.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig3_domains.pdf",bbox_inches="tight")
plt.close(fig)

print(f"rendered · tasks={len(cat)} items={sum(r['n_items'] for r in cat):,} ratings={sum(r['n_ratings'] for r in cat):,} median_r={np.median(allr):.3f}")
