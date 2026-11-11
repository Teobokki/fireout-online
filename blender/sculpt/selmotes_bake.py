# Bake SELMOTES face decals: for each character model, project the skin texture onto a small conforming patch over the
# mouth, inpaint the neutral lips and paint SMILE / GOOFY FROWN mouths. Output: assets/models/face_<bam>.json + assets/tex/face_<bam>_<expr>.png
import numpy as np, sys, json, os
from PIL import Image, ImageDraw, ImageFilter
from panda3d.core import *
loadPrcFileData('','window-type none\naudio-library-name null')
from direct.showbase.ShowBase import ShowBase
b=ShowBase()
ROOT='/workspace/fireout-shine'
HEAD_O=np.array([0.0,-0.030,1.578])
def rz(a): c,s=np.cos(a),np.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def rx(a): c,s=np.cos(a),np.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def ry(a): c,s=np.cos(a),np.sin(a); return np.array([[c,0,s],[0,1,0],[-s,0,c]])
HEAD_R=rz(np.radians(16))@rx(np.radians(3))@ry(np.radians(-7))
REG={'mouth':(-0.058,0.058,-0.106,-0.030),'brow':(-0.062,0.062,0.017,0.060)}
X0=X1=Z0=Z1=0;W=H=0
def setreg(r):
    global X0,X1,Z0,Z1,W,H
    X0,X1,Z0,Z1=REG[r]; W=480; H=int(480*(Z1-Z0)/(X1-X0))
def tris(path):
    m=b.loader.load_model(path); P=[];U=[];N=[]
    for np_ in m.find_all_matches('**/skin/+GeomNode'):
        mat=np_.get_mat(m)
        for g in np_.node().get_geoms():
            vd=g.get_vertex_data(); col='texcoord.0' if vd.get_format().has_column(InternalName.make('texcoord.0')) else 'texcoord'
            rv=GeomVertexReader(vd,'vertex'); rt=GeomVertexReader(vd,col); rn=GeomVertexReader(vd,'normal')
            pv=[];tv=[];nv=[]
            while not rv.is_at_end():
                v=mat.xform_point(rv.get_data3()); pv.append((v.x,v.y,v.z)); t=rt.get_data2(); tv.append((t.x,t.y)); n=mat.xform_vec(rn.get_data3()); nv.append((n.x,n.y,n.z))
            pv=np.array(pv);tv=np.array(tv);nv=np.array(nv)
            gd=g.decompose()
            for p in range(gd.get_num_primitives()):
                pr=gd.get_primitive(p)
                for k in range(pr.get_num_primitives()):
                    s=pr.get_primitive_start(k); idx=[pr.get_vertex(s+j) for j in range(3)]
                    P.append(pv[idx]);U.append(tv[idx]);N.append(nv[idx])
    return np.array(P),np.array(U),np.array(N)
def bake(bam, skin):
    P,UV,NN=tris(f'{ROOT}/assets/models/{bam}.bam')
    Q=(P-HEAD_O)@HEAD_R; NQ=NN@HEAD_R
    depth=np.full((H,W),np.inf); uv=np.zeros((H,W,2)); nrm=np.zeros((H,W,3))
    xs=X0+(np.arange(W)+0.5)/W*(X1-X0); zs=Z1-(np.arange(H)+0.5)/H*(Z1-Z0)
    for t in range(len(Q)):
        q=Q[t]
        if q[:,1].max()>-0.004: continue
        if q[:,0].max()<X0 or q[:,0].min()>X1 or q[:,2].max()<Z0 or q[:,2].min()>Z1: continue
        a,bb,c=q[:,[0,2]]
        d=(bb[1]-c[1])*(a[0]-c[0])+(c[0]-bb[0])*(a[1]-c[1])
        if abs(d)<1e-12: continue
        c0=max(0,int((q[:,0].min()-X0)/(X1-X0)*W)-1); c1=min(W,int((q[:,0].max()-X0)/(X1-X0)*W)+2)
        r0=max(0,int((Z1-q[:,2].max())/(Z1-Z0)*H)-1); r1=min(H,int((Z1-q[:,2].min())/(Z1-Z0)*H)+2)
        if c0>=c1 or r0>=r1: continue
        gx,gz=np.meshgrid(xs[c0:c1],zs[r0:r1])
        l1=((bb[1]-c[1])*(gx-c[0])+(c[0]-bb[0])*(gz-c[1]))/d; l2=((c[1]-a[1])*(gx-c[0])+(a[0]-c[0])*(gz-c[1]))/d; l3=1-l1-l2
        ins=(l1>=-1e-4)&(l2>=-1e-4)&(l3>=-1e-4)
        y=l1*q[0,1]+l2*q[1,1]+l3*q[2,1]
        sub=depth[r0:r1,c0:c1]; upd=ins&(y<sub)
        if not upd.any(): continue
        sub[upd]=y[upd]
        for k in range(2): uv[r0:r1,c0:c1,k][upd]=(l1*UV[t,0,k]+l2*UV[t,1,k]+l3*UV[t,2,k])[upd]
        for k in range(3): nrm[r0:r1,c0:c1,k][upd]=(l1*NQ[t,0,k]+l2*NQ[t,1,k]+l3*NQ[t,2,k])[upd]
    cov=np.isfinite(depth); print(bam,'coverage %.3f'%cov.mean())
    sk=np.asarray(Image.open(f'{ROOT}/assets/tex/{skin}.png').convert('RGB')).astype(float); th,tw=sk.shape[:2]
    px=np.clip((uv[...,0]%1)*tw,0,tw-1).astype(int); py=np.clip((1-(uv[...,1]%1))*th,0,th-1).astype(int)
    img=sk[py,px]; img[~cov]=img[cov].mean(axis=0)
    # uncovered depth: nearest covered pixel in the row (keeps grid vertices on the face instead of popping forward)
    for r in range(H):
        cs=np.where(cov[r])[0]
        if len(cs)==0: continue
        for c in np.where(~cov[r])[0]: depth[r,c]=depth[r,cs[np.argmin(np.abs(cs-c))]]
    return dict(depth=depth,cov=cov,img=img,nrm=nrm,xs=xs,zs=zs)
def M(x,z): return ((x-X0)/(X1-X0)*W,(Z1-z)/(Z1-Z0)*H)
def feather(im,cov,k=0.14):
    fx=np.minimum(np.arange(W),W-1-np.arange(W))/(W*k); fz=np.minimum(np.arange(H),H-1-np.arange(H))/(H*k)
    a=np.clip(np.minimum.outer(fz,fx),0,1); a=a*a*(3-2*a)
    cm=np.asarray(Image.fromarray((cov*255).astype(np.uint8)).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(4))).astype(float)/255
    a=a*cm
    arr=np.asarray(im.convert('RGBA')).copy(); arr[...,3]=(a*255).astype(np.uint8); return Image.fromarray(arr)
def blob(ov,box,col,blur):
    l=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(l).ellipse([*M(box[0],box[3]),*M(box[2],box[1])],fill=col)
    ov.alpha_composite(l.filter(ImageFilter.GaussianBlur(blur)))
def curve(f,xa,xb,n=32): return [(xa+(xb-xa)*i/n, f(xa+(xb-xa)*i/n)) for i in range(n+1)]
def strokes(ov,pts,col,w,blur=1.2):
    l=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(l).line([M(*p) for p in pts],fill=col,width=w,joint='curve')
    ov.alpha_composite(l.filter(ImageFilter.GaussianBlur(blur)))
def polyl(ov,pts,col,blur=0.8):
    l=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(l).polygon([M(*p) for p in pts],fill=col); ov.alpha_composite(l.filter(ImageFilter.GaussianBlur(blur)))
def paint_mouth(base,expr,dan):
    img=base['img'].copy(); cov=base['cov']
    gx,gz=np.meshgrid(base['xs'],base['zs']); e=((gx-0.0)/0.0265)**2+((gz+0.0725)/0.0195)**2
    lipcol=img[(e<0.3)&cov].mean(axis=0); skin=img[(e>1.6)&(e<3)&cov].mean(axis=0)
    out=img.copy(); lip=e<1.0
    for c in range(W):
        rows=np.where(lip[:,c])[0]
        if len(rows)==0: continue
        a,bq=rows[0]-2,rows[-1]+2
        if a<0 or bq>=H: continue
        ca,cb=img[max(0,a-3):a+1,c].mean(0),img[bq:bq+4,c].mean(0)
        for r in rows: f=(r-a)/(bq-a); out[r,c]=ca*(1-f)+cb*f
    im=Image.fromarray(np.clip(out,0,255).astype(np.uint8))
    mk=Image.fromarray((np.clip(1.3-e,0,1)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    im=Image.composite(im.filter(ImageFilter.GaussianBlur(3)),im,mk).convert('RGBA')
    lc=tuple(int(min(255,v)) for v in (lipcol*np.array([1.08,0.82,0.85]) if not dan else lipcol*np.array([1.0,0.85,0.85])))
    dark=(55,14,20); sh=tuple(int(v*0.62) for v in skin)
    ov=Image.new('RGBA',(W,H),(0,0,0,0))
    if expr=='smile':
        hw=0.031
        top=lambda x:-0.0655-0.0035*(1-(x/hw)**2)+0.0060*(x/hw)**4
        bot=lambda x:-0.0645-0.0215*max(0.0,1-(x/hw)**2)**1.3
        ulip=lambda x:top(x)+0.0040*(1-(x/(hw+0.001))**2)
        llip=lambda x:bot(x)-0.0045*(1-(x/(hw+0.001))**2)
        for sx in (-1,1):   # squinted, lifted cheeks + smile lines
            blob(ov,(sx*0.036-0.014,-0.050,sx*0.036+0.014,-0.031),(255,235,225,95),7)
            blob(ov,(sx*0.040-0.013,-0.050,sx*0.040+0.013,-0.038),(235,110,110,70),6)
            strokes(ov,[(sx*0.022,-0.032),(sx*0.034,-0.029),(sx*0.046,-0.033)],sh+(120,),5,2.0)
            strokes(ov,[(sx*0.017,-0.050),(sx*0.027,-0.056),(sx*0.034,-0.064),(sx*0.0355,-0.072)],sh+(170,),5,1.6)
        polyl(ov,curve(ulip,-hw-0.001,hw+0.001)+curve(llip,hw+0.001,-hw-0.001)[1:],lc+(255,))
        polyl(ov,curve(top,-hw,hw)+curve(bot,hw,-hw)[1:],dark+(255,))
        teeth=lambda x:top(x)-0.0068*(1-(x/(hw-0.003))**2)
        polyl(ov,curve(top,-hw+0.004,hw-0.004)+curve(teeth,hw-0.004,-hw+0.004)[1:],(250,248,240,255),0.6)
        tl=lambda x:-0.0655-0.0035*(1-(x/hw)**2)-0.0195*max(0.0,1-(x/hw)**2)**1.3*0.6
        polyl(ov,curve(lambda x:bot(x)+0.0002,-0.014,0.014)+curve(lambda x:bot(x)+0.0055*(1-(x/0.014)**2),0.014,-0.014)[1:],(200,80,90,230))  # tongue
        for sx in (-1,1): strokes(ov,[(sx*(hw-0.001),top(hw)),(sx*(hw+0.003),top(hw)+0.0025)],sh+(200,),4,1.0)
    else:
        hw=0.026
        top=lambda x:-0.0700+0.0055*(1-(x/hw)**2)-0.0135*(x/hw)**2
        bot=lambda x:-0.0745+0.0060*(1-(x/hw)**2)-0.0160*(x/hw)**2
        ulip=lambda x:top(x)+0.0055*(1-(x/(hw+0.001))**2)
        llip=lambda x:bot(x)-0.0140*max(0.0,1-(x/(hw+0.0015))**2)**0.8
        blob(ov,(-0.024,-0.104,0.024,-0.084),sh+(150,),5)            # shadow under the pushed-out lower lip
        polyl(ov,curve(ulip,-hw-0.001,hw+0.001)+curve(llip,hw+0.0015,-hw-0.0015)[1:],lc+(255,))
        polyl(ov,curve(top,-hw,hw)+curve(bot,hw,-hw)[1:],dark+(255,))
        blob(ov,(-0.013,-0.088,0.013,-0.080),(255,225,225,170),2.5)   # glossy pout highlight
        for sx in (-1,1):
            strokes(ov,[(sx*hw,top(hw)),(sx*(hw+0.004),top(hw)-0.006),(sx*(hw+0.003),top(hw)-0.012)],sh+(190,),5,1.2)
            strokes(ov,[(sx*0.018,-0.050),(sx*0.026,-0.058),(sx*0.031,-0.068)],sh+(110,),4,1.6)
        for k in range(3): strokes(ov,[(-0.009+k*0.009,-0.098),(-0.008+k*0.009,-0.101)],sh+(120,),3,1.0)   # scrunched chin
    im.alpha_composite(ov); return feather(im,cov)
def paint_brow(base,expr,dan):
    im=Image.fromarray(np.clip(base['img'],0,255).astype(np.uint8)).convert('RGBA'); cov=base['cov']
    skin=base['img'][cov].mean(axis=0); sh=tuple(int(v*0.62) for v in skin)
    bc=(40,26,20) if dan else (52,34,28)
    ov=Image.new('RGBA',(W,H),(0,0,0,0))
    if expr=='frown':        # raised, scrunched inner brows + worried forehead
        for sx in (-1,1):
            strokes(ov,[(sx*0.007,0.043),(sx*0.016,0.039),(sx*0.027,0.031),(sx*0.038,0.025)],bc+(245,),12,1.4)
            strokes(ov,[(sx*0.0045,0.036),(sx*0.0055,0.025)],sh+(170,),4,1.2)        # scrunch lines between the brows
        for k,z in enumerate((0.049,0.054)):
            strokes(ov,curve(lambda x,z=z:z+0.004*(1-(x/0.02)**2),-0.020,0.020,12),sh+(130,),4,1.6)
    else:                    # smile: brows lifted and relaxed
        pass
    a=np.asarray(ov)[...,3].astype(float)/255; fz=feather(Image.new('RGBA',(W,H)),cov,0.1); a*=np.asarray(fz)[...,3]/255
    arr=np.asarray(ov).copy(); arr[...,3]=(a*255).astype(np.uint8); return Image.fromarray(arr)
def mesh(base,nx=40,nz=28):
    dep=base['depth']; nrm=base['nrm']; V=[]
    for j in range(nz+1):
        for i in range(nx+1):
            u=i/nx; v=j/nz; c=min(W-1,int(u*W)); r=min(H-1,int((1-v)*H))
            y=dep[r,c] if np.isfinite(dep[r,c]) else np.nanmin(np.where(np.isfinite(dep),dep,np.nan))
            n=nrm[r,c]; L=np.linalg.norm(n) or 1; n=n/L
            q=np.array([X0+u*(X1-X0), y-0.0011, Z0+v*(Z1-Z0)])
            p=q@HEAD_R.T+HEAD_O; nw=n@HEAD_R.T
            V.append([round(float(t),5) for t in (*p,*nw,u,v)])
    return dict(nx=nx,nz=nz,v=V)
jobs=[('heroine','skin_c'),('heroine_crop','skin_c_crop'),('heroine_bikini','skin_c_bikini'),('heroine_police','skin_c_police'),('daniel','skin_c_daniel'),('daniel_swim','skin_c_swim'),('miyoyazu','skin_c_miyo')]
for bam,skin in jobs:
    if len(sys.argv)>1 and bam not in sys.argv[1:]: continue
    dan=bam.startswith('daniel'); regs={}
    for r in ('mouth','brow'):
        setreg(r); base=bake(bam,skin); regs[r]=dict(mesh(base),box=REG[r])
        for e in ('smile','frown'): (paint_mouth if r=='mouth' else paint_brow)(base,e,dan).save(f'{ROOT}/assets/tex/face_{bam}_{e}_{r}.png')
    json.dump(dict(regions=regs),open(f'{ROOT}/assets/models/face_{bam}.json','w'))
