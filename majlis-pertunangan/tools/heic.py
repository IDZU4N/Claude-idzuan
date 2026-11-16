import sys,glob,os
from PIL import Image, ImageOps, ImageDraw
import pillow_heif
pillow_heif.register_heif_opener()
S=sys.argv[1]
fs=sorted(glob.glob(S+'/src/*.HEIC'))
th=[]
for f in fs:
    im=ImageOps.exif_transpose(Image.open(f)).convert('RGB')
    n=os.path.basename(f)[:-5]
    im.save(f'{S}/img/{n}.jpg',quality=95)
    print(n,im.size)
    t=im.copy(); t.thumbnail((480,480)); th.append((n,t))
# contact sheets of 12
for k in range(0,len(th),12):
    sh=Image.new('RGB',(4*490,3*510),(20,20,20)); d=ImageDraw.Draw(sh)
    for i,(n,t) in enumerate(th[k:k+12]):
        x,y=(i%4)*490,(i//4)*510
        sh.paste(t,(x+5,y+25)); d.text((x+8,y+8),n,fill=(255,255,255))
    sh.save(f'{S}/sheets/photos_{k//12}.jpg',quality=85)
