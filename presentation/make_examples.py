import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Circle
HERE=os.path.dirname(os.path.abspath(__file__))
SANS="Helvetica" if "Helvetica" in {f.name for f in fm.fontManager.ttflist} else "Arial"
INK="#1a1a1a"; MUT="#6b6b6b"; FAINT="#9a9a9a"; CARD="#ffffff"; BORDER="#e3e3df"; PAGE="#f4f4f2"
plt.rcParams.update({"font.family":SANS,"pdf.fonttype":42,"svg.fonttype":"none"})

# domain -> color (matches the other figures)
COL={"Form":"#C1699B","Syntax":"#D8622A","Affective":"#12507F",
     "Perceptual / motor":"#4A90C2","Conceptual":"#7FB4D8","Sentence semantics":"#159C7B"}

# examples in figure order (Form, Syntax, then 3 Lexical, then Sentence semantics)
EX=[
 dict(name="FORM",color=COL["Form"],dim="iconicity · does it sound like its meaning?",scale="1–7",
      hi=("high","“oomph”","6.9",0.98), lo=("low","“how”","1.3",0.05), ends=("not iconic","very iconic")),
 dict(name="SYNTAX",color=COL["Syntax"],dim="grammaticality · is it well-formed?",scale="% grammatical",
      hi=("high","“a nice small German electric bike”","97%",0.97),
      lo=("low","“an electric German small nice bike”","11%",0.11), ends=("ungrammatical","grammatical")),
 dict(name="LEXICAL · AFFECTIVE",color=COL["Affective"],dim="valence · positive or negative?",scale="1–9",
      hi=("high","“vacation”","8.5",0.94), lo=("low","“murder”","1.5",0.06), ends=("negative","positive")),
 dict(name="LEXICAL · PERCEPTUAL / MOTOR",color=COL["Perceptual / motor"],dim="concreteness · abstract or concrete?",scale="1–5",
      hi=("high","“yo-yo”","5.0",1.0), lo=("low","“belief”","1.2",0.05), ends=("abstract","concrete")),
 dict(name="LEXICAL · CONCEPTUAL",color=COL["Conceptual"],dim="age of acquisition · when is it learned?",scale="years",
      hi=("late","“penury”","21 yr",0.84), lo=("early","“momma”","2 yr",0.08), ends=("early","late")),
 dict(name="SENTENCE SEMANTICS",color=COL["Sentence semantics"],dim="plausibility · does it make sense?",scale="1–7",
      hi=("high","“The operator stopped the machine.”","7.0",1.0),
      lo=("low","“The mountain had been promptly delivered.”","1.3",0.05), ends=("nonsense","makes sense")),
]

fig=plt.figure(figsize=(14.5,8.2)); fig.patch.set_facecolor(PAGE)
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")

# title
ax.text(0.035,0.955,"What the model actually sees",fontsize=23,weight="bold",color=INK,va="top")
ax.text(0.035,0.905,"One real example from each level — the model is given the very same instruction a human received.",
        fontsize=12.5,color=MUT,va="top")

# grid geometry
L,R=0.035,0.965; cols=3; cgap=0.022
cw=(R-L-(cols-1)*cgap)/cols
top,bot=0.855,0.175; rgap=0.045; ch=(top-bot-rgap)/2
def card_xy(i):
    r,c=divmod(i,cols)
    x=L+c*(cw+cgap); y=top-ch-r*(ch+rgap)
    return x,y

def draw(i,e):
    x,y=card_xy(i)
    ax.add_patch(FancyBboxPatch((x,y),cw,ch,boxstyle="round,pad=0,rounding_size=0.012",
                 mutation_aspect=fig.get_figwidth()/fig.get_figheight(),
                 fc=CARD,ec=BORDER,lw=1.0,zorder=1))
    pad=0.014; ix=x+pad; iw=cw-2*pad; cy=y+ch-0.030
    # domain name
    ax.text(ix,cy,e["name"],fontsize=11.5,weight="bold",color=e["color"],va="top")
    cy-=0.052
    ax.text(ix,cy,e["dim"],fontsize=10,color=MUT,va="top")
    cy-=0.020
    ax.text(ix+iw,cy+0.019,"scale "+e["scale"],fontsize=8.3,color=FAINT,va="top",ha="right")
    # rule
    cy-=0.010
    ax.plot([ix,ix+iw],[cy,cy],color=e["color"],lw=1.4,alpha=0.85,zorder=2)
    cy-=0.040
    # example rows
    for lab,txt,score,pos in (e["hi"],e["lo"]):
        tfs = 9.0 if len(txt)>36 else (9.9 if len(txt)>24 else 10.4)
        ax.text(ix,cy,lab,fontsize=8.5,weight="bold",color=e["color"],va="center",ha="left")
        ax.text(ix+0.050,cy,txt,fontsize=tfs,color=INK,va="center",ha="left")
        ax.text(ix+iw,cy,score,fontsize=13,weight="bold",color=e["color"],va="center",ha="right")
        cy-=0.052
    # mini scale bar
    cy-=0.006
    bx0,bx1=ix,ix+iw
    ax.plot([bx0,bx1],[cy,cy],color="#dcdcd8",lw=2.4,solid_capstyle="round",zorder=2)
    for (lab,txt,score,pos),filled in ((e["hi"],True),(e["lo"],False)):
        px=bx0+pos*(bx1-bx0)
        ax.add_patch(Circle((px,cy),0.006,fc=(e["color"] if filled else "#ffffff"),
                     ec=e["color"],lw=1.4,zorder=3,transform=ax.transData))
    ax.text(bx0,cy-0.026,e["ends"][0],fontsize=7.6,color=FAINT,va="top",ha="left")
    ax.text(bx1,cy-0.026,e["ends"][1],fontsize=7.6,color=FAINT,va="top",ha="right")

for i,e in enumerate(EX): draw(i,e)

# footer: instruction-adaptation callout
fy=0.045; fh=0.088
ax.add_patch(FancyBboxPatch((L,fy),R-L,fh,boxstyle="round,pad=0,rounding_size=0.010",
             mutation_aspect=fig.get_figwidth()/fig.get_figheight(),fc="#eef2f5",ec="#d5dee4",lw=1.0,zorder=1))
ax.text(L+0.016,fy+fh-0.020,"EACH ITEM IS DROPPED INTO THE ORIGINAL HUMAN INSTRUCTION — UNCHANGED",
        fontsize=9,weight="bold",color="#3a6a86",va="top")
ax.text(L+0.016,fy+0.030,
        "“Please rate the word  yo-yo  on a scale from 1 (abstract) to 5 (concrete). Answer with one digit.”",
        fontsize=11,color=INK,va="center",style="italic")

fig.savefig(f"{HERE}/fig_examples.png",dpi=300,facecolor=PAGE,bbox_inches="tight")
fig.savefig(f"{HERE}/fig_examples.pdf",facecolor=PAGE,bbox_inches="tight")
print("wrote fig_examples.png / .pdf")
