import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

OUT="/workspace/fireout-online-phones/"
S=2  # supersample
W,H=1600*S,1200*S
INTER="/usr/share/fonts/truetype/sand-box/google/Inter/Inter-VariableFont_opsz,wght.ttf"
CJK="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
CJKR="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
def F(sz,w="Bold"):
    f=ImageFont.truetype(INTER,sz)
    try: f.set_variation_by_name(w)
    except Exception: pass
    return f
def J(sz,bold=True): return ImageFont.truetype(CJK if bold else CJKR,sz,index=0)

def vgrad(w,h,stops):
    y=np.linspace(0,1,h)[:,None]
    out=np.zeros((h,w,3))
    for c in range(3):
        xs=[s[0] for s in stops]; vs=[s[1][c] for s in stops]
        out[:,:,c]=np.interp(y,xs,vs)
    return Image.fromarray(out.astype(np.uint8),"RGB")

def glow(base,layer,radius,strength=1.0):
    g=layer.filter(ImageFilter.GaussianBlur(radius))
    if strength!=1.0:
        g=Image.eval(g,lambda v:min(255,int(v*strength)))
    return ImageChops.add(base,g)

def rmask(size,r):
    m=Image.new("L",size,0); ImageDraw.Draw(m).rounded_rectangle([0,0,size[0]-1,size[1]-1],r,fill=255); return m

# ---------------- backgrounds ----------------
def background(seed=1):
    rnd=random.Random(seed)
    bg=vgrad(W,H,[(0,(8,6,22)),(0.6,(14,8,34)),(1,(4,4,12))])
    lay=Image.new("RGB",(W,H),0); d=ImageDraw.Draw(lay)
    for (x,y,r,c) in [(0.15,0.25,500,(255,0,140)),(0.88,0.2,560,(0,200,255)),(0.8,0.9,500,(150,0,255)),(0.1,0.9,420,(0,255,200))]:
        d.ellipse([x*W-r,y*H-r,x*W+r,y*H+r],fill=tuple(int(v*0.35) for v in c))
    bg=ImageChops.add(bg,lay.filter(ImageFilter.GaussianBlur(220)))
    # perspective grid floor
    g=Image.new("RGB",(W,H),0); d=ImageDraw.Draw(g)
    hz=int(H*0.62)
    for i in range(-30,31):
        d.line([(W/2+i*40*S,hz),(W/2+i*420*S,H)],fill=(120,0,160),width=2*S)
    for k in range(1,16):
        y=hz+(H-hz)*(k/15)**2.2
        d.line([(0,y),(W,y)],fill=(120,0,160),width=2*S)
    fade=vgrad(W,H,[(0,(0,0,0)),(0.62,(0,0,0)),(0.75,(180,180,180)),(1,(255,255,255))]).convert("L")
    g=Image.composite(g,Image.new("RGB",(W,H),0),fade)
    bg=glow(ImageChops.add(bg,Image.eval(g,lambda v:int(v*0.5))),g,6*S,0.8)
    # bokeh
    b=Image.new("RGB",(W,H),0); d=ImageDraw.Draw(b)
    for _ in range(40):
        x,y=rnd.random()*W,rnd.random()*H*0.65; r=rnd.uniform(8,40)*S
        c=rnd.choice([(255,40,160),(0,200,255),(255,200,60),(160,80,255)])
        d.ellipse([x-r,y-r,x+r,y+r],fill=tuple(int(v*0.25) for v in c))
    bg=ImageChops.add(bg,b.filter(ImageFilter.GaussianBlur(6*S)))
    return bg

def branding(img,sub):
    d=ImageDraw.Draw(img)
    t=Image.new("RGB",img.size,0); td=ImageDraw.Draw(t)
    td.text((60*S,48*S),"FIREOUT ONLINE",font=F(46*S,"Black"),fill=(255,40,170))
    td.text((62*S,104*S),"ファイアアウト・オンライン",font=J(24*S),fill=(0,220,255))
    img=glow(img,t,10*S,1.2); img=ImageChops.add(img,t)
    d=ImageDraw.Draw(img)
    d.text((60*S,H-90*S),sub,font=F(22*S,"SemiBold"),fill=(200,200,230))
    d.text((60*S,H-58*S),"EX IX G9  ·  EX Inc. / EX Inc.",font=F(18*S,"Medium"),fill=(130,130,170))
    return img

# ---------------- wallpapers ----------------
def wall_tokyo(w,h,seed=7):
    rnd=random.Random(seed)
    img=vgrad(w,h,[(0,(10,4,40)),(0.45,(60,10,90)),(0.62,(150,30,110)),(0.7,(30,8,50)),(1,(6,4,16))])
    d=ImageDraw.Draw(img)
    for _ in range(120):
        x,y=rnd.random()*w,rnd.random()*h*0.4; d.point((x,y),fill=(200,200,255))
    neon=Image.new("RGB",(w,h),0); nd=ImageDraw.Draw(neon)
    hz=int(h*0.66)
    # far skyline
    x=0
    while x<w:
        bw=rnd.randint(w//16,w//7); bh=rnd.randint(int(h*0.12),int(h*0.32))
        d.rectangle([x,hz-bh,x+bw,hz],fill=(28,14,52))
        x+=bw-rnd.randint(0,10)
    # near buildings
    x=-20
    while x<w:
        bw=rnd.randint(w//8,w//4); bh=rnd.randint(int(h*0.25),int(h*0.55))
        top=hz-bh; col=(12,8,26)
        d.rectangle([x,top,x+bw,hz],fill=col)
        for wy in range(top+20,hz-10,22):
            for wx in range(x+10,x+bw-10,18):
                if rnd.random()<0.35:
                    c=rnd.choice([(255,210,140),(140,220,255),(255,150,210)])
                    d.rectangle([wx,wy,wx+8,wy+10],fill=tuple(int(v*0.7) for v in c))
        if rnd.random()<0.8:
            c=rnd.choice([(255,30,150),(0,230,255),(255,220,40),(160,60,255),(255,80,40)])
            sx=x+bw//2-24; sy=top+rnd.randint(30,max(31,bh//3))
            txt=rnd.choice(["ネオン","ラーメン","カラオケ","東京","バー","ホテル","夜"])
            if rnd.random()<0.5:
                ty=sy
                for ch in txt:
                    nd.text((sx,ty),ch,font=J(40),fill=c); ty+=44
                nd.rectangle([sx-8,sy-8,sx+48,ty+4],outline=c,width=4)
            else:
                nd.rounded_rectangle([x+10,sy,x+bw-10,sy+50],10,outline=c,width=5)
                nd.text((x+22,sy+2),txt,font=J(34),fill=c)
        x+=bw+rnd.randint(-10,20)
    # road
    d.polygon([(0,h),(w,h),(w*0.62,hz),(w*0.38,hz)],fill=(14,10,24))
    d.rectangle([0,hz,w,hz+4],fill=(40,20,60))
    # light trails
    for i in range(14):
        c=(255,40,60) if i%2 else (255,240,220)
        off=rnd.uniform(-0.1,0.1)
        x0=w*(0.45+off*0.3); x1=w*(0.0+i/13.0)
        nd.line([(x0,hz+6),(x1,h)],fill=c,width=rnd.randint(3,8))
    # center dashes
    for k in range(10):
        t0=(k/10)**2; t1=((k+0.5)/10)**2
        nd.line([(w/2,hz+(h-hz)*t0),(w/2,hz+(h-hz)*t1)],fill=(255,220,80),width=int(2+10*t1))
    img=glow(img,neon,18,1.4); img=glow(img,neon,5,1.0); img=ImageChops.add(img,Image.eval(neon,lambda v:int(v*0.8)))
    # wet reflection
    refl=img.crop((0,hz-int(h*0.3),w,hz)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(6))
    refl=refl.resize((w,h-hz-4))
    rm=vgrad(w,h-hz-4,[(0,(110,110,110)),(1,(0,0,0))]).convert("L")
    img.paste(Image.blend(img.crop((0,hz+4,w,h)),refl,0.45),(0,hz+4),rm)
    return img

def wall_beach(w,h,seed=3):
    rnd=random.Random(seed)
    hz=int(h*0.58)
    img=vgrad(w,h,[(0,(40,30,110)),(0.25,(160,60,140)),(0.45,(255,120,90)),(0.58,(255,200,120)),(0.585,(60,60,120)),(0.75,(30,40,90)),(0.78,(220,170,120)),(1,(180,120,80))])
    d=ImageDraw.Draw(img)
    sun=Image.new("RGB",(w,h),0); sd=ImageDraw.Draw(sun)
    cx,cy,r=w*0.5,hz-30,150
    sd.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(255,230,150))
    sd.rectangle([0,hz,w,h],fill=0)
    img=glow(img,sun,80,0.9); img=ImageChops.add(img,Image.eval(sun,lambda v:int(v*0.8)))
    d=ImageDraw.Draw(img)
    # clouds
    for _ in range(7):
        x=rnd.random()*w; y=rnd.uniform(0.1,0.4)*h; cw=rnd.randint(150,350)
        cl=Image.new("L",(w,h),0); ImageDraw.Draw(cl).ellipse([x-cw,y-22,x+cw,y+22],fill=160)
        img.paste((255,170,170),(0,0),cl.filter(ImageFilter.GaussianBlur(14)))
    # sun reflection on sea
    seaH=int(h*0.78)
    for k in range(40):
        y=hz+5+(seaH-hz-10)*k/40; ww=rnd.uniform(40,200)*(1+k/30)
        d.line([(cx-ww,y),(cx+ww,y)],fill=(255,210,140),width=3)
    # waves foam
    for k in range(3):
        y=seaH-6+k*10
        pts=[(x,y+6*math.sin(x/40+k)) for x in range(0,w+10,10)]
        d.line(pts,fill=(255,235,210),width=4)
    # palm
    def palm(bx,by,hgt,lean):
        pts=[]
        for i in range(30):
            t=i/29; pts.append((bx+lean*t*t,by-hgt*t))
        for i in range(29):
            d.line([pts[i],pts[i+1]],fill=(25,10,25),width=int(30-16*i/29))
        tx,ty=pts[-1]
        for a in range(0,360,36):
            ang=math.radians(a+rnd.uniform(-10,10)); L=rnd.uniform(220,320)
            prev=(tx,ty)
            for j in range(1,16):
                t=j/15
                p=(tx+math.cos(ang)*L*t, ty-math.sin(ang)*L*t*0.6+ (L*0.5)*t*t)
                d.line([prev,p],fill=(25,10,25),width=int(22*(1-t))+2); prev=p
    palm(w*0.12,h,h*0.62,120); palm(w*0.9,h,h*0.5,-90)
    return img

# ---------------- icons ----------------
def icon_contacts(sz):
    im=vgrad(sz,sz,[(0,(60,220,170)),(1,(10,130,150))])
    d=ImageDraw.Draw(im)
    c=sz/2
    d.ellipse([c-sz*0.15,sz*0.2,c+sz*0.15,sz*0.5],fill=(255,255,255))
    d.chord([c-sz*0.29,sz*0.54,c+sz*0.29,sz*1.08],180,360,fill=(255,255,255))
    d.rectangle([sz*0.80,sz*0.25,sz*0.86,sz*0.33],fill=(255,255,255,));d.rectangle([sz*0.80,sz*0.45,sz*0.86,sz*0.53],fill=(255,255,255))
    out=Image.new("RGBA",(sz,sz)); out.paste(im,(0,0),rmask((sz,sz),int(sz*0.24))); return out
def icon_taxi(sz):
    im=vgrad(sz,sz,[(0,(30,30,40)),(1,(10,10,16))])
    d=ImageDraw.Draw(im)
    # checker band
    for i in range(10):
        for j in range(2):
            if (i+j)%2==0: d.rectangle([i*sz/10,sz*0.82+j*sz*0.05,(i+1)*sz/10,sz*0.82+(j+1)*sz*0.05],fill=(255,200,0))
    y=sz*0.38
    d.rounded_rectangle([sz*0.30,y-sz*0.12,sz*0.70,y+sz*0.05],int(sz*0.06),fill=(255,200,0))
    d.rounded_rectangle([sz*0.16,y,sz*0.84,y+sz*0.22],int(sz*0.07),fill=(255,200,0))
    d.rectangle([sz*0.35,y-sz*0.08,sz*0.48,y+sz*0.02],fill=(60,70,90)); d.rectangle([sz*0.52,y-sz*0.08,sz*0.65,y+sz*0.02],fill=(60,70,90))
    d.rounded_rectangle([sz*0.42,y-sz*0.2,sz*0.58,y-sz*0.12],4,fill=(255,60,60))
    for xx in (0.3,0.7):
        d.ellipse([sz*xx-sz*0.08,y+sz*0.14,sz*xx+sz*0.08,y+sz*0.30],fill=(20,20,20),outline=(200,200,200),width=max(2,sz//60))
    d.ellipse([sz*0.18,y+sz*0.06,sz*0.25,y+sz*0.12],fill=(255,255,220)); d.ellipse([sz*0.75,y+sz*0.06,sz*0.82,y+sz*0.12],fill=(255,255,220))
    f=F(int(sz*0.13),"Black"); d.text((sz/2,sz*0.08),"JP TAXI",font=f,fill=(255,200,0),anchor="mt")
    out=Image.new("RGBA",(sz,sz)); out.paste(im,(0,0),rmask((sz,sz),int(sz*0.24))); return out

# ---------------- screen UI ----------------
SW,SH=1080,2340
def status_bar(img,dark_text=False,time="23:41"):
    d=ImageDraw.Draw(img); col=(255,255,255)
    d.text((70,62),time,font=F(44,"SemiBold"),fill=col,anchor="lm")
    x=SW-70
    # battery
    d.rounded_rectangle([x-70,44,x-8,80],8,outline=col,width=4); d.rectangle([x-6,54,x,70],fill=col)
    d.rounded_rectangle([x-64,50,x-30,74],4,fill=col)
    d.text((x-82,62),"57%",font=F(30,"Medium"),fill=col,anchor="rm")
    # signal
    sx=x-210
    for i in range(4):
        hh=10+i*8; d.rectangle([sx+i*14,80-hh,sx+i*14+9,80],fill=col if i<3 else (150,150,150))
    # wifi
    wx,wy=sx-50,80
    for r in (36,24,12):
        d.arc([wx-r,wy-r,wx+r,wy+r],225,315,fill=col,width=6)
    d.text((sx-110,62),"5G",font=F(28,"Bold"),fill=col,anchor="mm")
def shadow_text(img,xy,txt,font,fill,anchor="la"):
    sh=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(sh).text((xy[0]+3,xy[1]+4),txt,font=font,fill=(0,0,0,170),anchor=anchor)
    sh=sh.filter(ImageFilter.GaussianBlur(6)); img.alpha_composite(sh); ImageDraw.Draw(img).text(xy,txt,font=font,fill=fill,anchor=anchor)
def home_screen(wall,name,greet_jp):
    img=wall.resize((SW,SH)).convert("RGBA")
    top=vgrad(SW,500,[(0,(0,0,0)),(1,(0,0,0))]).convert("RGBA"); a=vgrad(SW,500,[(0,(120,120,120)),(1,(0,0,0))]).convert("L"); top.putalpha(a)
    img.alpha_composite(top)
    status_bar(img)
    shadow_text(img,(SW/2,330),"23:41",F(230,"Light"),(255,255,255),"mm")
    shadow_text(img,(SW/2,480),"WED 21 OCT  ·  18°C",F(40,"Medium"),(230,230,240),"mm")
    # greeting pill
    pill=Image.new("RGBA",img.size,(0,0,0,0)); pd=ImageDraw.Draw(pill)
    pd.rounded_rectangle([SW/2-330,560,SW/2+330,700],70,fill=(10,10,25,140),outline=(255,255,255,70),width=2)
    img.alpha_composite(pill)
    d=ImageDraw.Draw(img)
    d.text((SW/2,612),f"Good evening, {name}",font=F(50,"SemiBold"),fill=(255,255,255),anchor="mm")
    d.text((SW/2,666),greet_jp,font=J(30,False),fill=(200,220,255),anchor="mm")
    # icons
    isz=210; y=1700
    for i,(ic,lab) in enumerate([(icon_contacts(isz),"Contacts"),(icon_taxi(isz),"JP TAXI")]):
        cx=SW/2+(-170 if i==0 else 170)
        sh=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([cx-isz/2+6,y+14,cx+isz/2+6,y+isz+14],50,fill=(0,0,0,160))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        img.alpha_composite(ic,(int(cx-isz/2),y))
        shadow_text(img,(cx,y+isz+50),lab,F(40,"SemiBold"),(255,255,255),"mm")
    # nav pill
    ImageDraw.Draw(img).rounded_rectangle([SW/2-150,SH-50,SW/2+150,SH-38],6,fill=(255,255,255,220))
    return img

def contacts_screen():
    img=Image.new("RGBA",(SW,SH),(14,14,22,255)); d=ImageDraw.Draw(img)
    status_bar(img)
    d.text((70,230),"Contacts",font=F(96,"Bold"),fill=(255,255,255))
    d.text((74,350),"連絡先  ·  2 contacts",font=J(34,False),fill=(150,150,175))
    d.rounded_rectangle([60,430,SW-60,530],50,fill=(34,34,48))
    d.ellipse([110,460,146,496],outline=(150,150,170),width=5); d.line([(140,490),(158,508)],fill=(150,150,170),width=6)
    d.text((180,480),"Search",font=F(40,"Regular"),fill=(130,130,150),anchor="lm")
    rows=[("Emergency Services","110 / 119",(230,50,60),"SOS"),("JP Taxi","Dispatch · 24h",(255,190,0),"TX")]
    y=600
    d.text((70,y),"ALL",font=F(32,"SemiBold"),fill=(120,120,145)); y+=60
    for nm,sub,c,ini in rows:
        d.rounded_rectangle([50,y,SW-50,y+190],36,fill=(26,26,38))
        d.ellipse([90,y+35,210,y+155],fill=c)
        d.text((150,y+95),ini,font=F(44,"Black"),fill=(255,255,255) if ini=="SOS" else (20,20,20),anchor="mm")
        d.text((250,y+72),nm,font=F(54,"SemiBold"),fill=(255,255,255),anchor="lm")
        d.text((250,y+130),sub,font=F(36,"Regular"),fill=(150,150,175),anchor="lm")
        # call button
        bx=SW-150; by=y+95
        d.ellipse([bx-50,by-50,bx+50,by+50],fill=(40,190,110))
        d.arc([bx-24,by-24,bx+24,by+24],100,260,fill=(255,255,255),width=12)
        y+=220
    d.text((SW/2,SH-200),"EX IX G9",font=F(30,"Medium"),fill=(70,70,90),anchor="mm")
    d.rounded_rectangle([SW/2-150,SH-50,SW/2+150,SH-38],6,fill=(255,255,255,200))
    return img

# ---------------- crack ----------------
def crack_overlay(w,h,origin,seed=11):
    rnd=random.Random(seed)
    L=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(L)
    ox,oy=origin
    rays=[]
    n=13
    for i in range(n):
        ang=math.radians(-100+ i*(110/(n-1)) + rnd.uniform(-3,3))  # spread across glass from bottom-left
        length=rnd.uniform(0.4,1.3)*math.hypot(w,h)*0.7
        pts=[(ox,oy)]; x,y=ox,oy; a=ang
        steps=int(length/40)
        for s in range(steps):
            a+=rnd.uniform(-0.12,0.12); seg=rnd.uniform(25,55)
            x+=math.cos(a)*seg; y+=math.sin(a)*seg; pts.append((x,y))
        rays.append(pts)
    def line(pts,wid,a):
        d.line(pts,fill=(0,0,0,int(a*0.6)),width=wid+3)
        d.line([(p[0]+1.5,p[1]+1.5) for p in pts],fill=(255,255,255,int(a*0.35)),width=wid+2)
        d.line(pts,fill=(240,248,255,a),width=wid)
    for pts in rays:
        line(pts,4 if len(pts)>30 else 3,230)
        # branches
        for k in range(3,len(pts)-3,rnd.randint(5,9)):
            if rnd.random()<0.3:
                x,y=pts[k]; a=math.atan2(pts[k+1][1]-y,pts[k+1][0]-x)+rnd.choice([-1,1])*rnd.uniform(0.4,0.9)
                bp=[(x,y)]
                for s in range(rnd.randint(3,9)):
                    a+=rnd.uniform(-0.2,0.2); x+=math.cos(a)*30; y+=math.sin(a)*30; bp.append((x,y))
                line(bp,2,190)
    # concentric rings connecting rays
    for ring in range(1,9):
        idx=int(ring*2.2)
        for i in range(len(rays)-1):
            if rnd.random()<0.75 and idx<len(rays[i]) and idx<len(rays[i+1]):
                p1=rays[i][idx]; p2=rays[i+1][min(idx+rnd.randint(-1,1),len(rays[i+1])-1)]
                mid=((p1[0]+p2[0])/2+rnd.uniform(-10,10),(p1[1]+p2[1])/2+rnd.uniform(-10,10))
                line([p1,mid,p2],2 if ring>3 else 3,200)
    # impact shatter
    sh=Image.new("RGBA",(w,h),(0,0,0,0)); sd=ImageDraw.Draw(sh)
    for _ in range(80):
        r=rnd.uniform(0,160); a=rnd.uniform(-math.pi,0.3)
        x,y=ox+math.cos(a)*r,oy+math.sin(a)*r
        pts=[(x+rnd.uniform(-30,30),y+rnd.uniform(-30,30)) for _ in range(3)]
        sd.polygon(pts,fill=(255,255,255,rnd.randint(30,110)),outline=(255,255,255,200))
    L.alpha_composite(sh)
    g=Image.new("RGBA",(w,h),(0,0,0,0)); ImageDraw.Draw(g).ellipse([ox-220,oy-220,ox+220,oy+220],fill=(255,255,255,60))
    L.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    return L

def crack_screen(scr,origin,seed=5):
    rnd=random.Random(seed)
    w,h=scr.size; ox,oy=origin
    L=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(L)
    M=Image.new("L",(w,h),0); md=ImageDraw.Draw(M)
    def line(pts,wid,a):
        md.line(pts,fill=255,width=wid+10)
        d.line([(p[0]+3,p[1]+3) for p in pts],fill=(0,0,0,110),width=wid+3)
        d.line(pts,fill=(235,242,255,a),width=wid)
        d.line([(p[0]-1,p[1]-1) for p in pts],fill=(255,255,255,int(a*0.5)),width=max(1,wid-2))
    rays=[]
    angs=[-88,-72,-55,-38,-22,-8,6,-140,175]
    for A in angs:
        a=math.radians(A+rnd.uniform(-4,4)); x,y=ox,oy; pts=[(x,y)]
        while -50<x<w+50 and -50<y<h+50:
            seg=rnd.uniform(120,260); a+=rnd.uniform(-0.06,0.06)
            x+=math.cos(a)*seg; y+=math.sin(a)*seg; pts.append((x,y))
        rays.append(pts); line(pts,4,240)
        # a couple of short sharp side splits
        for k in range(1,len(pts)-1):
            if rnd.random()<0.25:
                bx,by=pts[k]; ba=a+rnd.choice([-1,1])*rnd.uniform(0.35,0.6); bl=rnd.uniform(80,200)
                line([(bx,by),(bx+math.cos(ba)*bl,by+math.sin(ba)*bl)],2,200)
    # partial concentric rings
    for R in (100,210,330):
        a0=rnd.uniform(-math.pi,0); span=rnd.uniform(1.6,2.6); n=9
        pts=[]
        for i in range(n+1):
            t=a0+span*i/n; rr=R*rnd.uniform(0.94,1.06)
            pts.append((ox+math.cos(t)*rr,oy+math.sin(t)*rr))
        line(pts,3,210)
    # refraction: shifted wallpaper along cracks
    shifted=ImageChops.offset(scr,6,-5).filter(ImageFilter.GaussianBlur(1))
    scr.paste(Image.blend(scr,shifted,0.9),(0,0),M.filter(ImageFilter.GaussianBlur(2)))
    # impact cluster
    sh=Image.new("RGBA",(w,h),(0,0,0,0)); sd=ImageDraw.Draw(sh)
    for _ in range(140):
        r=abs(rnd.gauss(0,38)); a=rnd.uniform(-math.pi,math.pi)
        x,y=ox+math.cos(a)*r,oy+math.sin(a)*r; s_=rnd.uniform(6,22)
        pts=[(x+rnd.uniform(-s_,s_),y+rnd.uniform(-s_,s_)) for _ in range(3)]
        sd.polygon(pts,fill=(255,255,255,rnd.randint(40,150)),outline=(255,255,255,230))
    for _ in range(14):
        a=rnd.uniform(-math.pi,math.pi); r=rnd.uniform(50,90)
        sd.line([(ox,oy),(ox+math.cos(a)*r,oy+math.sin(a)*r)],fill=(255,255,255,220),width=2)
    g=Image.new("RGBA",(w,h),(0,0,0,0)); ImageDraw.Draw(g).ellipse([ox-90,oy-90,ox+90,oy+90],fill=(255,255,255,90))
    scr.alpha_composite(g.filter(ImageFilter.GaussianBlur(35)))
    scr.alpha_composite(L); scr.alpha_composite(sh)
    gl=Image.new("RGBA",(w,h),(0,0,0,0)); ImageDraw.Draw(gl).ellipse([ox-14,oy-14,ox+14,oy+14],fill=(255,255,255,255))
    scr.alpha_composite(gl.filter(ImageFilter.GaussianBlur(6)))
    return scr

# ---------------- phone rendering ----------------
def phone_front(screen,frame,ph):
    pw=int(ph*SW/SH*1.035); r=int(pw*0.14)
    pad=60
    lay=Image.new("RGBA",(pw+2*pad,ph+2*pad),(0,0,0,0))
    # shadow
    shm=Image.new("L",lay.size,0); ImageDraw.Draw(shm).rounded_rectangle([pad+20,pad+40,pad+pw+20,pad+ph+40],r,fill=200)
    shadow=Image.new("RGBA",lay.size,(0,0,0,255)); shadow.putalpha(shm.filter(ImageFilter.GaussianBlur(40)))
    lay.alpha_composite(shadow)
    # side buttons
    bd=ImageDraw.Draw(lay)
    dk=tuple(int(c*0.6) for c in frame)
    bd.rounded_rectangle([pad+pw-6,pad+int(ph*0.18),pad+pw+8,pad+int(ph*0.27)],6,fill=dk)
    bd.rounded_rectangle([pad+pw-6,pad+int(ph*0.30),pad+pw+8,pad+int(ph*0.36)],6,fill=dk)
    bd.rounded_rectangle([pad-8,pad+int(ph*0.22),pad+6,pad+int(ph*0.30)],6,fill=dk)
    # frame: metallic horizontal gradient
    fr=np.zeros((ph,pw,3)); x=np.linspace(0,1,pw)[None,:]
    shade=0.55+0.6*np.exp(-((x-0.08)/0.05)**2)+0.35*np.exp(-((x-0.93)/0.04)**2)+0.25*x
    for c in range(3): fr[:,:,c]=np.clip(frame[c]*shade,0,255)
    frI=Image.fromarray(fr.astype(np.uint8)).convert("RGBA")
    lay.paste(frI,(pad,pad),rmask((pw,ph),r))
    # inner black glass
    b=int(pw*0.022)
    gm=rmask((pw-2*b,ph-2*b),r-b)
    lay.paste((6,6,8,255),(pad+b,pad+b),gm)
    # screen
    sb=int(pw*0.024)
    sw,sh=pw-2*b-2*sb,ph-2*b-2*sb
    scr=screen.resize((sw,sh),Image.LANCZOS)
    lay.paste(scr,(pad+b+sb,pad+b+sb),rmask((sw,sh),r-b-sb))
    sd=ImageDraw.Draw(lay)
    # punch hole
    cx=pad+pw//2; cy=pad+b+sb+int(sh*0.025); cr=int(pw*0.022)
    sd.ellipse([cx-cr,cy-cr,cx+cr,cy+cr],fill=(4,4,6)); sd.ellipse([cx-cr//2,cy-cr//2,cx-cr//6,cy-cr//6],fill=(40,50,80))
    # glass reflection
    refl=Image.new("RGBA",lay.size,(0,0,0,0)); rd=ImageDraw.Draw(refl)
    rd.polygon([(pad,pad),(pad+pw*0.55,pad),(pad,pad+ph*0.45)],fill=(255,255,255,22))
    rm=Image.new("L",lay.size,0); rm.paste(gm,(pad+b,pad+b))
    lay.paste(Image.alpha_composite(lay,refl),(0,0),rm)
    # rim highlight
    sd.rounded_rectangle([pad,pad,pad+pw-1,pad+ph-1],r,outline=tuple(min(255,int(c*1.4)+40) for c in frame)+(140,),width=3)
    return lay,(pad+b+sb,pad+b+sb,sw,sh,r-b-sb)

def phone_back(frame,glass,ph):
    pw=int(ph*SW/SH*1.035); r=int(pw*0.14); pad=60
    lay=Image.new("RGBA",(pw+2*pad,ph+2*pad),(0,0,0,0))
    shm=Image.new("L",lay.size,0); ImageDraw.Draw(shm).rounded_rectangle([pad+20,pad+40,pad+pw+20,pad+ph+40],r,fill=200)
    shadow=Image.new("RGBA",lay.size,(0,0,0,255)); shadow.putalpha(shm.filter(ImageFilter.GaussianBlur(40))); lay.alpha_composite(shadow)
    fr=np.zeros((ph,pw,3)); x=np.linspace(0,1,pw)[None,:]
    shade=0.55+0.6*np.exp(-((x-0.92)/0.05)**2)+0.3*np.exp(-((x-0.06)/0.04)**2)
    for c in range(3): fr[:,:,c]=np.clip(frame[c]*shade,0,255)
    lay.paste(Image.fromarray(fr.astype(np.uint8)),(pad,pad),rmask((pw,ph),r))
    b=int(pw*0.02)
    gw,gh=pw-2*b,ph-2*b
    g=np.zeros((gh,gw,3)); yy,xx=np.mgrid[0:gh,0:gw]; t=(xx/gw*0.6+yy/gh*0.4)
    sheen=0.85+0.35*np.exp(-((t-0.3)/0.12)**2)-0.15*t
    for c in range(3): g[:,:,c]=np.clip(glass[c]*sheen,0,255)
    lay.paste(Image.fromarray(g.astype(np.uint8)),(pad+b,pad+b),rmask((gw,gh),r-b))
    d=ImageDraw.Draw(lay)
    # camera module
    mx,my=pad+b+int(gw*0.07),pad+b+int(gw*0.07); mw=int(gw*0.46)
    msh=Image.new("RGBA",lay.size,(0,0,0,0)); ImageDraw.Draw(msh).rounded_rectangle([mx+6,my+10,mx+mw+6,my+mw+10],int(mw*0.25),fill=(0,0,0,120))
    lay.alpha_composite(msh.filter(ImageFilter.GaussianBlur(12)))
    d=ImageDraw.Draw(lay)
    d.rounded_rectangle([mx,my,mx+mw,my+mw],int(mw*0.25),fill=tuple(int(c*0.82) for c in glass),outline=tuple(min(255,int(c*1.15)) for c in glass),width=3)
    lr=int(mw*0.19)
    for (fx,fy) in [(0.3,0.3),(0.3,0.72),(0.72,0.5)]:
        cx,cy=mx+mw*fx,my+mw*fy
        d.ellipse([cx-lr,cy-lr,cx+lr,cy+lr],fill=(30,34,30),outline=(170,180,170),width=4)
        d.ellipse([cx-lr*0.62,cy-lr*0.62,cx+lr*0.62,cy+lr*0.62],fill=(8,10,20))
        d.ellipse([cx-lr*0.4,cy-lr*0.45,cx-lr*0.1,cy-lr*0.15],fill=(70,90,140))
    d.ellipse([mx+mw*0.72-12,my+mw*0.2-12,mx+mw*0.72+12,my+mw*0.2+12],fill=(255,240,200))
    # EX mark
    d.text((pad+pw/2,pad+ph*0.52),"EX",font=F(int(pw*0.16),"Black"),fill=tuple(int(c*0.7) for c in glass),anchor="mm")
    d.text((pad+pw/2,pad+ph*0.90),"EX IX G9",font=F(int(pw*0.045),"SemiBold"),fill=tuple(int(c*0.62) for c in glass),anchor="mm")
    d.rounded_rectangle([pad,pad,pad+pw-1,pad+ph-1],r,outline=tuple(min(255,int(c*1.3)+30) for c in frame)+(150,),width=3)
    return lay

def label(img,xy,txt,color):
    t=Image.new("RGB",img.size,0); ImageDraw.Draw(t).text(xy,txt,font=F(30*S,"Bold"),fill=color,anchor="mm")
    return ImageChops.add(glow(img,t,8*S,1.2),t)

def neon_ring(img,cx,cy,rx,ry,color):
    t=Image.new("RGB",img.size,0); ImageDraw.Draw(t).ellipse([cx-rx,cy-ry,cx+rx,cy+ry],outline=color,width=4*S)
    return ImageChops.add(glow(img,t,16*S,1.5),t)

def finish(img,name): img.resize((W//S,H//S),Image.LANCZOS).save(OUT+name); print("saved",name)

# ===== ANA =====
BLUE=(40,90,220)
bg=background(1); bg=neon_ring(bg,W//2,int(H*0.93),900*S,80*S,(0,180,255))
scr=home_screen(wall_tokyo(SW,SH),"ANA","こんばんは、アナ")
scr=crack_screen(scr,(120,SH-150))
ph=int(1000*S)
front,_=phone_front(scr,BLUE,ph)
back=phone_back(BLUE,(70,125,235),ph)
# wear on back: corner chip + light scratches
bw,bh=back.size; wd=ImageDraw.Draw(back); pad=60
rr=random.Random(9)
cx,cy=bw-pad-70,bh-pad-60
chip=[(cx+rr.uniform(-28,28),cy+rr.uniform(-22,22)) for _ in range(7)]
wd.polygon(chip,fill=(200,215,240,170),outline=(255,255,255,230))
wd.line([(bw-pad-30,bh-pad-130),(bw-pad-18,bh-pad-90)],fill=(225,235,255,200),width=3)
for (x0,y0,x1,y1) in [(0.25,0.6,0.55,0.66),(0.5,0.35,0.78,0.31),(0.3,0.78,0.45,0.83)]:
    wd.line([(pad+x0*(bw-2*pad),pad+y0*(bh-2*pad)),(pad+x1*(bw-2*pad),pad+y1*(bh-2*pad))],fill=(220,232,255,90),width=2)
img=bg.convert("RGBA")
y=(H-front.height)//2+20*S
img.alpha_composite(front,(W//2-front.width+30*S,y)); img.alpha_composite(back,(W//2-30*S,y))
img=img.convert("RGB")
img=label(img,(W//2-front.width//2+30*S,y+4*S),"FRONT",(110,190,255)); img=label(img,(W//2+back.width//2-30*S,y+4*S),"BACK",(110,190,255))
img=branding(img,"ANA'S PHONE  ·  BLUE  ·  SCREEN DAMAGED")
finish(img,"ana_phone.png")

# ===== DANIEL =====
GREEN=(120,200,60); GLASS=(150,215,95)
bg=background(2); bg=neon_ring(bg,W//2,int(H*0.93),900*S,80*S,(140,255,80))
scr=home_screen(wall_beach(SW,SH),"DANIEL","こんばんは、ダニエル")
ph=int(1000*S)
front,_=phone_front(scr,GREEN,ph)
back=phone_back(GREEN,GLASS,ph)
img=bg.convert("RGBA")
y=(H-front.height)//2+20*S
img.alpha_composite(front,(W//2-front.width+30*S,y)); img.alpha_composite(back,(W//2-30*S,y))
img=img.convert("RGB")
img=label(img,(W//2-front.width//2+30*S,y+4*S),"FRONT",(160,255,110)); img=label(img,(W//2+back.width//2-30*S,y+4*S),"BACK",(160,255,110))
img=branding(img,"DANIEL'S PHONE  ·  APPLE GREEN")
finish(img,"daniel_phone.png")

# ===== CONTACTS =====
bg=background(3); bg=neon_ring(bg,W//2,int(H*0.93),560*S,70*S,(255,60,170))
lay,_=phone_front(contacts_screen(),(70,70,90),int(1060*S))
img=bg.convert("RGBA"); img.alpha_composite(lay,((W-lay.width)//2,(H-lay.height)//2+10*S))
img=branding(img.convert("RGB"),"CONTACTS APP  ·  EMERGENCY + TAXI")
finish(img,"contacts_screen.png")
