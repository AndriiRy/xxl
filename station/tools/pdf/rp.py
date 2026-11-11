import numpy as np, struct, sys, json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
def stl(fn):
    d=open(fn,"rb").read()
    if d[:5]==b"solid" and b"facet" in d[:300]:
        V=[list(map(float,l.split()[1:])) for l in d.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        return np.array(V).reshape(-1,3,3)
    n=struct.unpack("<I",d[84-4:84])[0]
    return np.frombuffer(d[84:84+n*50],dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]))["v"].reshape(-1,3,3).astype(float)
parts=sys.argv[2:]; out={}
for p in parts:
    T=stl(f"{sys.argv[1]}/{p}.stl")
    vol=abs(np.einsum('ij,ij->i',T[:,0],np.cross(T[:,1],T[:,2])).sum()/6)/1000
    mn,mx=T.reshape(-1,3).min(0),T.reshape(-1,3).max(0)
    out[p]={"vol":round(vol,1),"size":[round(x) for x in (mx-mn)]}
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); n/=np.linalg.norm(n,axis=1)[:,None]+1e-12
    L=np.array([0.35,-0.55,0.76]); L/=np.linalg.norm(L); s=0.35+0.65*np.clip(n@L,0,1)*0.8+0.2*np.abs(n@L)
    s=np.clip(s,0,1)
    fig=plt.figure(figsize=(3,3)); ax=fig.add_subplot(projection="3d")
    c=np.array([0.27,0.45,0.66]) if p in("alidade","pod_lid_l","pod_lid_r") else (np.array([0.85,0.86,0.87]) if p.startswith("head") or p.startswith("target") else (np.array([0.93,0.55,0.2]) if p=="v_drum" else (np.array([0.15,0.15,0.17]) if p=="foot" else np.array([0.45,0.47,0.52]))))
    ax.add_collection3d(Poly3DCollection(T,facecolors=np.clip(s[:,None]*c[None,:]*1.25,0,1),edgecolors="none"))
    ctr=(mn+mx)/2; r=(mx-mn).max()/2
    ax.set_xlim(ctr[0]-r,ctr[0]+r); ax.set_ylim(ctr[1]-r,ctr[1]+r); ax.set_zlim(ctr[2]-r,ctr[2]+r)
    ax.set_box_aspect((1,1,1)); ax.view_init(24,-58); ax.axis("off")
    plt.subplots_adjust(0,0,1,1); plt.savefig(f"img/{p}.png",dpi=110,transparent=False,facecolor="white"); plt.close(fig)
    print(p,out[p],len(T),flush=True)
json.dump(out,open("parts.json","w"))
