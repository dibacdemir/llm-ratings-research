import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch
HERE=os.path.dirname(os.path.abspath(__file__))
SANS="Helvetica" if "Helvetica" in {f.name for f in fm.fontManager.ttflist} else "Arial"
INK="#1a1a1a"; MUT="#6b6b6b"; FAINT="#9a9a9a"; CARD="#ffffff"; BORDER="#e3e3df"; PAGE="#f4f4f2"
plt.rcParams.update({"font.family":SANS,"pdf.fonttype":42,"svg.fonttype":"none"})

COL={"Form":"#C1699B","Syntax":"#D8622A","Affective":"#12507F",
     "Perceptual / motor":"#4A90C2","Conceptual":"#7FB4D8","Sentence semantics":"#159C7B"}

# all examples on 1–N rating scales; each card: short question + high/low pair + mean score
EX=[
 dict(name="FORM",color=COL["Form"],dim="iconicity · does it sound like its meaning?",scale="1–7",
      hi=("high","“oomph”","6.9"), lo=("low","“how”","1.3")),
 dict(name="SYNTAX",color=COL["Syntax"],dim="naturalness · how natural is the sentence?",scale="1–7",
      hi=("high","“Who thought that John stole something?”","6.9"),
      lo=("low","“Who stood that Susan stole something?”","1.4")),
 dict(name="LEXICAL · AFFECTIVE",color=COL["Affective"],dim="valence · positive or negative?",scale="1–9",
      hi=("high","“vacation”","8.5"), lo=("low","“murder”","1.5")),
 dict(name="LEXICAL · PERCEPTUAL / MOTOR",color=COL["Perceptual / motor"],dim="concreteness · abstract or concrete?",scale="1–5",
      hi=("high","“yo-yo”","5.0"), lo=("low","“belief”","1.2")),
 dict(name="LEXICAL · CONCEPTUAL",color=COL["Conceptual"],dim="socialness · how social is its meaning?",scale="1–7",
      hi=("high","“friendship”","7.0"), lo=("low","“sulfur”","1.2")),
 dict(name="SENTENCE SEMANTICS",color=COL["Sentence semantics"],dim="plausibility · does it make sense?",scale="1–7",
      hi=("high","“The operator stopped the machine.”","7.0"),
      lo=("low","“The mountain had been promptly delivered.”","1.3")),
]

fig=plt.figure(figsize=(14.5,7.6)); fig.patch.set_facecolor(PAGE)
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")

ax.text(0.035,0.955,"What the model actually sees",fontsize=23,weight="bold",color=INK,va="top")
ax.text(0.035,0.902,"One real example from each level — the model is given the very same instruction, and rating scale, a human received.",
        fontsize=12.5,color=MUT,va="top")

L,R=0.035,0.965; cols=3; cgap=0.024
cw=(R-L-(cols-1)*cgap)/cols
top,bot=0.845,0.235; rgap=0.05; ch=(top-bot-rgap)/2
def card_xy(i):
    r,c=divmod(i,cols); return L+c*(cw+cgap), top-ch-r*(ch+rgap)

def draw(i,e):
    x,y=card_xy(i); asp=fig.get_figwidth()/fig.get_figheight()
    ax.add_patch(FancyBboxPatch((x,y),cw,ch,boxstyle="round,pad=0,rounding_size=0.012",
                 mutation_aspect=asp,fc=CARD,ec=BORDER,lw=1.0,zorder=1))
    pad=0.017; ix=x+pad; iw=cw-2*pad; cy=y+ch-0.040
    ax.text(ix,cy,e["name"],fontsize=12,weight="bold",color=e["color"],va="top")
    cy-=0.058
    ax.text(ix,cy,e["dim"],fontsize=9.8,color=MUT,va="top")
    ax.text(ix+iw,cy,"scale "+e["scale"],fontsize=8.4,color=FAINT,va="top",ha="right")
    cy-=0.024
    ax.plot([ix,ix+iw],[cy,cy],color=e["color"],lw=1.5,alpha=0.85,zorder=2)
    cy-=0.066
    for lab,txt,score in (e["hi"],e["lo"]):
        tfs = 8.9 if len(txt)>40 else (9.8 if len(txt)>26 else 11)
        ax.text(ix,cy,lab,fontsize=8.6,weight="bold",color=e["color"],va="center",ha="left")
        ax.text(ix+0.052,cy,txt,fontsize=tfs,color=INK,va="center",ha="left")
        ax.text(ix+iw,cy,score,fontsize=15,weight="bold",color=e["color"],va="center",ha="right")
        cy-=0.075

for i,e in enumerate(EX): draw(i,e)

# footer: instruction-adaptation callout
fy=0.045; fh=0.10
ax.add_patch(FancyBboxPatch((L,fy),R-L,fh,boxstyle="round,pad=0,rounding_size=0.010",
             mutation_aspect=fig.get_figwidth()/fig.get_figheight(),fc="#eef2f5",ec="#d5dee4",lw=1.0,zorder=1))
ax.text(L+0.018,fy+fh-0.024,"EACH ITEM IS DROPPED INTO THE ORIGINAL HUMAN INSTRUCTION — UNCHANGED",
        fontsize=9.2,weight="bold",color="#3a6a86",va="top")
ax.text(L+0.018,fy+0.034,
        "“Please rate the word  yo-yo  on a scale from 1 (abstract) to 5 (concrete). Answer with one digit.”",
        fontsize=11.5,color=INK,va="center",style="italic")

fig.savefig(f"{HERE}/fig_examples.png",dpi=300,facecolor=PAGE,bbox_inches="tight")
fig.savefig(f"{HERE}/fig_examples.pdf",facecolor=PAGE,bbox_inches="tight")
print("wrote fig_examples.png / .pdf")
