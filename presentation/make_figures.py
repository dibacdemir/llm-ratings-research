import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import matplotlib.gridspec as gridspec
csv.field_size_limit(10**7)
HERE=os.path.dirname(os.path.abspath(__file__))

# ---------------- Nature-style global rcParams ----------------
_have={f.name for f in fm.fontManager.ttflist}
SANS = "Arial" if "Arial" in _have else ("Helvetica" if "Helvetica" in _have else "DejaVu Sans")
INK="#1a1a1a"; MUT="#5f5f5f"; AX="#8f8f8f"; GRID="#eeeeec"
plt.rcParams.update({
    "font.family":SANS,"font.size":9,"pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none",
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.linewidth":0.7,"axes.edgecolor":AX,"axes.labelcolor":INK,"axes.titlecolor":INK,"text.color":INK,
    "xtick.color":AX,"ytick.color":AX,"xtick.labelcolor":MUT,"ytick.labelcolor":MUT,
    "xtick.major.width":0.7,"ytick.major.width":0.7,"xtick.major.size":3,"ytick.major.size":3,
    "xtick.direction":"out","ytick.direction":"out","legend.frameon":False,
    "figure.facecolor":"white","savefig.facecolor":"white",
})

# domain display order (Andrea): form-side first (word form, sentence form),
# then meaning-side (word meaning = Lexical, sentence meaning = Semantics)
DOM_ORDER=["Form (sub-lexical)","Syntax","Lexical: affective","Lexical: perceptual/motor",
           "Lexical: conceptual","Sentence semantics"]
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
def spines(ax,keep=("left","bottom")):
    for k,s in ax.spines.items(): s.set_visible(k in keep)
    ax.tick_params(length=3)
_allr=[r['r'] for r in cat if r['r'] is not None]; OM=float(np.median(_allr))

# ---------------- panel drawers ----------------
def panel_coverage(ax, base_fs=9):
    HDR={"Form (sub-lexical)":"Form","Lexical: affective":"Affective",
         "Lexical: perceptual/motor":"Perceptual/\nmotor","Lexical: conceptual":"Conceptual",
         "Syntax":"Syntax","Sentence semantics":"Sentence\nsemantics"}
    xt=ax.get_xaxis_transform(); x=0; gap=9; spans={}
    for d in DOM_ORDER:
        grp=sorted([r for r in cat if r['domain']==d],key=lambda z:-z['n_items'])
        xs=np.arange(x,x+len(grp))
        ax.bar(xs,[g['n_items'] for g in grp],width=0.85,color=COL[d],linewidth=0,zorder=3)
        x0,x1,cx=x-0.6,x+len(grp)-0.4,x+len(grp)/2-0.5; spans[d]=(x0,x1,cx)
        ax.plot([x0,x1],[-0.018,-0.018],transform=xt,color=COL[d],lw=2.4,solid_capstyle="butt",clip_on=False,zorder=5)
        ax.text(cx,1.055,HDR[d],transform=xt,ha="center",va="bottom",fontsize=base_fs,weight="bold",
                color=LBLCOL[d],linespacing=0.92,clip_on=False)
        ax.text(cx,1.02,f"{dstats(d)[0]}",transform=xt,ha="center",va="bottom",fontsize=base_fs-1.5,color=MUT,clip_on=False)
        x+=len(grp)+gap
    lx0=spans["Lexical: affective"][0]; lx1=spans["Lexical: conceptual"][1]; lcx=(lx0+lx1)/2
    ax.plot([lx0,lx1],[1.17,1.17],transform=xt,color="#8fb8d8",lw=1.0,clip_on=False)
    for xx in (lx0,lx1): ax.plot([xx,xx],[1.16,1.17],transform=xt,color="#8fb8d8",lw=1.0,clip_on=False)
    ax.text(lcx,1.185,"LEXICAL · word meaning",transform=xt,ha="center",va="bottom",fontsize=base_fs-1.5,weight="bold",color="#5a93bd",clip_on=False)
    ax.set_yscale("log"); ax.set_ylim(60,100000); ax.set_xlim(-4,x-gap+2)
    ax.set_ylabel("Items per task  (words / sentences)",fontsize=base_fs)
    ax.set_xticks([]); ax.grid(axis="y",color=GRID,lw=0.7,zorder=0); ax.set_axisbelow(True)
    spines(ax,keep=("left",)); ax.tick_params(axis="x",length=0)
    ax.text(0.5,-0.055,"335 rating tasks · each bar = one task, ordered by size within domain",
            transform=ax.transAxes,ha="center",va="top",fontsize=base_fs-1.5,color=MUT)

def panel_composition(ax, base_fs=9):
    ys=np.arange(6)[::-1]; cols=[COL[d] for d in DOM_ORDER]
    ivals=[dstats(d)[1] for d in DOM_ORDER]; tvals=[dstats(d)[0] for d in DOM_ORDER]
    ax.barh(ys,ivals,height=0.62,color=cols,linewidth=0); ax.set_xscale("log")
    for y,iv,tv in zip(ys,ivals,tvals):
        ax.text(iv*1.25,y,f"{iv:,}",va="center",fontsize=base_fs-1,color=INK)
    ax.set_yticks(ys); ax.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER],fontsize=base_fs)
    ax.set_xlabel("Items per domain  (log scale)",fontsize=base_fs)
    ax.set_xlim(400,6_000_000); ax.grid(axis="x",color=GRID,lw=0.7); ax.set_axisbelow(True); spines(ax)

def panel_reliability(ax, base_fs=9):
    rng=np.random.default_rng(1)
    for i,d in enumerate(DOM_ORDER):
        rs=[r['r'] for r in cat if r['domain']==d and r['r'] is not None]
        y=i+rng.uniform(-0.16,0.16,len(rs))
        ax.scatter(rs,y,s=13,color=COL[d],alpha=0.75,edgecolor="white",linewidth=0.3,zorder=3)
        if rs:
            med=np.median(rs)
            ax.plot([med,med],[i-0.30,i+0.30],color=INK,lw=1.6,zorder=4,solid_capstyle="round")
            ax.text(1.008,i,f"{med:.2f}",va="center",fontsize=base_fs-1,color=MUT)
    ax.axvline(OM,color="#bcc1b9",ls=(0,(4,3)),lw=0.8,zorder=1)
    ax.set_yticks(range(6)); ax.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER],fontsize=base_fs)
    ax.set_ylim(5.6,-0.7); ax.set_xlim(0.45,1.0)
    ax.set_xlabel("Split-half reliability (Spearman–Brown)",fontsize=base_fs)
    ax.grid(axis="x",color=GRID,lw=0.7); ax.set_axisbelow(True); spines(ax)

def plabel(fig,ax,letter,dx=-0.06,dy=0.04):
    ax.text(dx,1.0+dy,letter,transform=ax.transAxes,fontsize=13,weight="bold",va="bottom",ha="left")

# ================= COMPOSITE Figure 1 =================
fig=plt.figure(figsize=(12.6,8.8))
gs=gridspec.GridSpec(2,2,figure=fig,height_ratios=[1.0,0.92],width_ratios=[1.05,1.0],
                     hspace=0.42,wspace=0.28,left=0.075,right=0.965,top=0.845,bottom=0.075)
axA=fig.add_subplot(gs[0,:]); panel_coverage(axA)
axB=fig.add_subplot(gs[1,0]); panel_composition(axB)
axC=fig.add_subplot(gs[1,1]); panel_reliability(axC)
plabel(fig,axA,"a",dx=-0.055,dy=0.10)
plabel(fig,axB,"b",dx=-0.20,dy=0.06)
plabel(fig,axC,"c",dx=-0.16,dy=0.06)
# panel a is labelled by its domain headers + the banner; b/c get short titles
axB.set_title("Dataset composition",fontsize=10,weight="bold",loc="left")
axC.set_title("Reliability of the human ratings",fontsize=10,weight="bold",loc="left")
# figure banner title
fig.text(0.02,0.965,"Figure 1  |  A broad, reliable atlas of human linguistic ratings for LLM evaluation",
         fontsize=13.5,weight="bold",ha="left",va="bottom")
fig.text(0.02,0.925,f"335 rating tasks · 6 linguistic domains · ~871,000 items · ~19.4M individual ratings · "
         f"median split-half r = {OM:.2f}",fontsize=9.5,color=MUT,ha="left",va="bottom")
fig.savefig(f"{HERE}/figure1_composite.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/figure1_composite.pdf",bbox_inches="tight")
plt.close(fig)

# ================= standalone panels (one-per-slide) =================
def standalone(drawer,fname,size,title,sub,base_fs=11,adj=None):
    fig,ax=plt.subplots(figsize=size); drawer(ax,base_fs=base_fs)
    ax.set_title(title,fontsize=14,weight="bold",loc="left",y=(1.30 if drawer is panel_coverage else 1.06))
    ax.text(0,(1.235 if drawer is panel_coverage else 1.01),sub,transform=ax.transAxes,fontsize=9.5,color=MUT)
    if adj: fig.subplots_adjust(**adj)
    fig.savefig(f"{HERE}/{fname}.png",dpi=300,bbox_inches="tight")
    fig.savefig(f"{HERE}/{fname}.pdf",bbox_inches="tight"); plt.close(fig)

standalone(panel_coverage,"fig1_coverage",(16,5.6),
           "Coverage across six levels of linguistic analysis",
           "each bar = one of 335 rating tasks · height = number of items · ordered by size within domain",
           adj=dict(top=0.72,left=0.06,right=0.985,bottom=0.08))
standalone(panel_reliability,"fig2_reliability",(8.8,5.0),
           "Human ratings are highly reliable",
           f"item-level split-half · 291 of 335 tasks with individual responses · overall median r = {OM:.2f}",
           adj=dict(top=0.86,left=0.22,right=0.93,bottom=0.12))
# fig3: composition in two panels — items (left) and human ratings (right) per domain
def hum(n):
    if n>=1e6: return f"{n/1e6:.1f}M"
    if n>=1e3: return f"{n/1e3:.0f}k"
    return str(int(n))
fig,(aL,aR)=plt.subplots(1,2,figsize=(11.5,4.6),gridspec_kw={"wspace":0.06})
ys=np.arange(6)[::-1]; cols=[COL[d] for d in DOM_ORDER]
ivals=[dstats(d)[1] for d in DOM_ORDER]; rvals=[dstats(d)[2] for d in DOM_ORDER]
aL.barh(ys,ivals,height=0.62,color=cols,linewidth=0); aL.set_xscale("log")
for y,v in zip(ys,ivals): aL.text(v*1.35,y,hum(v),va="center",fontsize=10,color=INK)
aL.set_yticks(ys); aL.set_yticklabels([d.replace("Lexical: ","Lex: ") for d in DOM_ORDER],fontsize=10.5)
aL.set_xlim(3e3,3e6); aL.set_xlabel("Items  (words / sentences)",fontsize=10.5)
aL.set_title("How many items",fontsize=12.5,weight="bold",loc="left")
aL.grid(axis="x",color=GRID,lw=0.7); aL.set_axisbelow(True); spines(aL)
aR.barh(ys,rvals,height=0.62,color=cols,linewidth=0); aR.set_xscale("log")
for y,v in zip(ys,rvals): aR.text(v*1.35,y,hum(v),va="center",fontsize=10,color=INK)
aR.set_yticks([]); aR.set_xlim(1e5,4e7); aR.set_xlabel("Individual human ratings",fontsize=10.5)
aR.set_title("How much human data",fontsize=12.5,weight="bold",loc="left")
aR.grid(axis="x",color=GRID,lw=0.7); aR.set_axisbelow(True); spines(aR)
aR.spines["left"].set_visible(False); aR.tick_params(axis="y",length=0)
fig.suptitle("Dataset composition by domain",fontsize=14,weight="bold",x=0.015,ha="left",y=1.02)
fig.subplots_adjust(top=0.85,left=0.15,right=0.985,bottom=0.13)
fig.savefig(f"{HERE}/fig3_domains.png",dpi=300,bbox_inches="tight")
fig.savefig(f"{HERE}/fig3_domains.pdf",bbox_inches="tight"); plt.close(fig)

print(f"rendered · tasks={len(cat)} items={sum(r['n_items'] for r in cat):,} "
      f"ratings={sum(r['n_ratings'] for r in cat):,} median_r={OM:.3f}")
