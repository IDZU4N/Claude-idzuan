from PIL import Image, ImageFilter, ImageDraw
import numpy as np, math, sys
rng=np.random.default_rng(7)
SRC='/home/user/Claude-idzuan/bunting-terapi-tok-wan/poster-asal.jpg'
CW,CH=2400,4800
CUTS=[int(x) for x in sys.argv[1].split(',')]      # cut rows in ORIGINAL poster coordinates
MARG=int(sys.argv[2])                               # top/bottom margin (px at 2400w)
CROP=(16,17,837,1257)
im=Image.open(SRC).convert('RGB').crop(CROP)
sc=CW/im.width
P=np.asarray(im.resize((CW,round(im.height*sc)),Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2,percent=60,threshold=2))).astype(np.float32)
PH=P.shape[0]
extra=CH-PH-2*MARG
n=len(CUTS); per=[extra//n+(1 if i<extra%n else 0) for i in range(n)]
def smooth(row,sigma):
    r=np.arange(-int(sigma*3),int(sigma*3)+1);k=np.exp(-r**2/(2*sigma**2));k/=k.sum()
    pad=np.pad(row,((len(k)//2,len(k)//2),(0,0)),mode='edge')
    return np.stack([np.convolve(pad[:,c],k,'valid') for c in range(3)],1)
base=np.array([2,12,32],np.float32)
def band(a_row,b_row,m,FD=14.0,sig=150,dark=0.0):
    Sa,Sb=smooth(a_row,sig),smooth(b_row,sig)
    out=np.zeros((m,CW,3),np.float32)
    for i in range(m):
        t=i/(m-1);sm=Sa*(1-t)+Sb*t
        sm=sm*(1-dark*math.sin(math.pi*t))+base*dark*math.sin(math.pi*t)
        wa=max(0,1-i/FD)**2; wb=max(0,1-(m-1-i)/FD)**2
        out[i]=sm*(1-wa-wb)+a_row*wa+b_row*wb
    return out
pieces=[];bands=[];y=0;prev=0
# top margin: replicate poster top edge smoothly toward darker navy
def edge(row,m,flip):
    S=smooth(row,150);out=np.zeros((m,CW,3),np.float32)
    for i in range(m):
        d=(1-i/(m-1)) if flip else i/(m-1)
        w=max(0,1-(m-1-i if flip else i)/50)**2
        out[i]=S*(1-0.3*d)+base*0.3*d
        out[i]=out[i]*(1-w)+row*w
    return out
top=edge(P[0:3].mean(0),MARG,True);pieces.append(top);bands.append((0,MARG));y=MARG
cs=[round((c-CROP[1])*sc) for c in CUTS]
for c,m in zip(cs,per):
    pieces.append(P[prev:c]);y+=c-prev
    pieces.append(band(P[c-3:c].mean(0),P[c:c+3].mean(0),m,dark=0.25));bands.append((y,y+m));y+=m;prev=c
pieces.append(P[prev:]);y+=PH-prev
bot=edge(P[-3:].mean(0),MARG,False);pieces.append(bot);bands.append((y,y+MARG))
bg=np.concatenate(pieces,0);assert bg.shape[0]==CH,bg.shape
out=bg
def glow(cx,cy,rx,ry,col,a):
    Y,X=np.ogrid[:CH,:CW];return np.exp(-(((X-cx)/rx)**2+((Y-cy)/ry)**2))[...,None]*np.array(col,np.float32)*a
def sparkle(cx,cy,r):
    sp=Image.new('L',(CW,CH),0);dd=ImageDraw.Draw(sp)
    pts=[(cx+(r if i%2==0 else r*.16)*math.sin(i*math.pi/4),cy-(r if i%2==0 else r*.16)*math.cos(i*math.pi/4)) for i in range(8)]
    dd.polygon(pts,fill=255)
    core=np.asarray(sp.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)/255
    halo=np.asarray(sp.filter(ImageFilter.GaussianBlur(r*.35))).astype(np.float32)/255
    return np.clip(core+halo*.8,0,1)[...,None]
def bez(p0,p1,p2,p3,k=300):
    return [((1-t)**3*p0[0]+3*(1-t)**2*t*p1[0]+3*(1-t)*t*t*p2[0]+t**3*p3[0],(1-t)**3*p0[1]+3*(1-t)**2*t*p1[1]+3*(1-t)*t*t*p2[1]+t**3*p3[1]) for t in [i/k for i in range(k+1)]]
cv=Image.new('L',(CW,CH),0);dc=ImageDraw.Draw(cv)
spk=np.zeros((CH,CW,1),np.float32)
for idx,(a,b) in enumerate(bands[1:-1],1):    # inner bands only get decor
    h=b-a
    if h<120: continue
    out=out+glow(CW/2,(a+b)/2,1000,h*.35,(70,110,220),.12)
    out=out+glow(CW/2,(a+b)/2,420,h*.12,(255,200,90),.05)
    fl=1 if idx%2 else -1
    pts=bez((0,a+h*(.5+.25*fl)),(700,a+h*(.5-.45*fl)),(1600,a+h*(.5+.45*fl)),(2400,a+h*(.5-.25*fl)))
    dc.line(pts,fill=160,width=5,joint='curve')
    pts=bez((0,a+h*(.58+.2*fl)),(700,a+h*(.58-.4*fl)),(1600,a+h*(.58+.4*fl)),(2400,a+h*(.58-.2*fl)))
    dc.line(pts,fill=100,width=2,joint='curve')
    for dx,dy,r in [(.14,.30,34),(.86,.62,30),(.5,.5,22)]:
        spk=np.maximum(spk,sparkle(CW*dx,a+h*dy,r))
for (a,b) in (bands[0],bands[-1]):
    spk=np.maximum(spk,sparkle(CW*.2,(a+b)/2,24)); spk=np.maximum(spk,sparkle(CW*.82,(a+b)/2,20))
xs=np.linspace(-1,1,CW)[None,:,None]
m=np.asarray(cv.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[...,None]/255
fade=.3+.7*np.abs(xs)**1.2
out=out*(1-m*fade*.8)+np.array([255,214,120],np.float32)*m*fade*.8
out=out*(1-spk)+np.array([255,244,200],np.float32)*spk
out+=rng.normal(0,1.2,out.shape).astype(np.float32)
# ---- frame ----
SS=2;W2,H2=CW*SS,CH*SS
def frame_mask(inset,width,notch):
    mk=Image.new('L',(W2,H2),0);dr=ImageDraw.Draw(mk)
    L,R,Tp,Bt=inset*SS,(CW-inset)*SS,inset*SS,(CH-inset)*SS;c=notch*SS;pts=[]
    def arc(cx,cy,a0,a1):
        for i in range(61):
            a=math.radians(a0+(a1-a0)*i/60);pts.append((cx+c*math.cos(a),cy+c*math.sin(a)))
    arc(L,Tp,90,0);arc(R,Tp,180,90);arc(R,Bt,270,180);arc(L,Bt,360,270);pts.append(pts[0])
    dr.line(pts,fill=255,width=width*SS,joint='curve')
    return mk.resize((CW,CH),Image.LANCZOS)
Y,X=np.mgrid[:CH,:CW].astype(np.float32)
v=.5+.5*np.cos(2*np.pi*(X/CW*.9+Y/CH*2.2))[...]
dark=np.array([150,92,16],np.float32);mid=np.array([226,170,55],np.float32);lite=np.array([255,240,175],np.float32)
col=np.where(v[...,None]<.5,dark+(mid-dark)*(v[...,None]*2),mid+(lite-mid)*((v[...,None]-.5)*2))
for inset,width,notch,alpha in [(40,9,92,1.0),(66,3,70,.85)]:
    mm=np.asarray(frame_mask(inset,width,notch)).astype(np.float32)[...,None]/255*alpha
    sh=np.asarray(Image.fromarray((mm[...,0]*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32)[...,None]/255
    out=out*(1-sh*.45);out=out*(1-mm)+col*mm
img=Image.fromarray(np.clip(out,0,255).astype(np.uint8))
img.save('k2.png',dpi=(100,100));img.save('k2.pdf',resolution=100.0,quality=95)
img.resize((600,1200),Image.LANCZOS).save('k2_prev.png');print(per,cs,PH)
