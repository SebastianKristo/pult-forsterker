"""Appbildet for Homey: S1, Node og Touch på et bord i en stue (kompositt av renderne i branding/homey_kilde)."""
import sys, os, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_homey_images import cutout
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
K=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'branding', 'homey_kilde') + '/'
W,H=2000,1400; random.seed(7)
def noise(w,h,scale,blur):
    n=Image.effect_noise((w//scale,h//scale),64).resize((w,h),Image.BICUBIC)
    return n.filter(ImageFilter.GaussianBlur(blur))
# vegg: varm puss med vindu-lys fra venstre
wall=Image.new('RGB',(W,H),(214,204,188))
light=Image.new('L',(W,H),0); ImageDraw.Draw(light).ellipse([-700,-500,1200,1100],fill=255)
light=light.filter(ImageFilter.GaussianBlur(320))
wall=Image.composite(Image.new('RGB',(W,H),(242,233,216)),wall,light)
shade=Image.new('L',(W,H),0); ImageDraw.Draw(shade).rectangle([0,0,W,H],fill=0)
grad=Image.linear_gradient('L').rotate(90,expand=True).resize((W,H))  # mørkere mot høyre
wall=Image.composite(Image.new('RGB',(W,H),(160,148,132)),wall,grad.point(lambda v:int(v*0.45)))
tex=noise(W,H,3,0.6); wall=ImageChops.overlay(wall,Image.merge('RGB',[tex.point(lambda v:118+(v-128)//6)]*3))
# vindusskygge (lys stripe) og bilde på veggen, uskarpt (dybdeskarphet)
d=ImageDraw.Draw(wall)
for x in (300,560): d.polygon([(x,0),(x+120,0),(x+420,880),(x+300,880)],fill=(247,239,224))
d.rectangle([1260,170,1700,500],fill=(58,50,44)); d.rectangle([1282,192,1678,478],fill=(222,213,196))
for i,c in enumerate([(196,120,80),(90,110,96),(214,170,110)]): d.rectangle([1320+i*120,250+i*30,1420+i*120,420],fill=c)
# plante (silhuett, uskarp)
pl=Image.new('RGBA',(W,H)); pd=ImageDraw.Draw(pl)
pd.rectangle([180,700,330,880],fill=(196,176,150,255))
for i in range(26):
    a=random.uniform(-2.6,-0.5); r=random.uniform(150,330); x0,y0=255,705
    x1,y1=x0+r*math.cos(a),y0+r*math.sin(a)
    pd.line([(x0,y0),(x1,y1)],fill=(70,96,62,255),width=7)
    pd.ellipse([x1-48,y1-26,x1+48,y1+26],fill=(78+random.randint(-12,12),112+random.randint(-12,12),70,255))
wall.paste(pl,(0,0),pl)
wall=wall.filter(ImageFilter.GaussianBlur(7))
# bord: eik med årer, perspektiv-mørkning
TOP=880
wood=Image.new('RGB',(W,H-TOP),(128,92,62))
gr=Image.effect_noise((W//60,(H-TOP)//2),70).resize((W,H-TOP),Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))
wood=ImageChops.overlay(wood,Image.merge('RGB',[gr.point(lambda v:128+(v-128)//4)]*3))
fade=Image.linear_gradient('L').resize((W,H-TOP)); wood=Image.composite(Image.new('RGB',(W,H-TOP),(86,58,38)),wood,fade.point(lambda v:int(v*0.55)))
wl=Image.new('L',(W,H-TOP),0); ImageDraw.Draw(wl).ellipse([-500,-400,1300,500],fill=110); wl=wl.filter(ImageFilter.GaussianBlur(200))
wood=Image.composite(Image.new('RGB',(W,H-TOP),(176,134,96)),wood,wl)
scene=wall.copy(); scene.paste(wood,(0,TOP))
ImageDraw.Draw(scene).rectangle([0,TOP-6,W,TOP+4],fill=(170,124,86))
scene=scene.convert('RGBA')
def place(dev,w,cx,bottom,refl=0.12,shadow=170):
    s=w/dev.width; dv=dev.resize((int(dev.width*s),int(dev.height*s)),Image.LANCZOS)
    x,y=int(cx-dv.width/2),int(bottom-dv.height)
    sh=Image.new('L',(W,H),0); ImageDraw.Draw(sh).ellipse([x+dv.width*.04,bottom-dv.height*.06,x+dv.width*.98,bottom+dv.height*.07],fill=shadow)
    sh=sh.filter(ImageFilter.GaussianBlur(dv.width*.035))
    scene.paste(Image.new('RGBA',(W,H),(28,18,10,255)),(0,0),sh)
    # svak refleks i bordet
    rf=dv.transpose(Image.FLIP_TOP_BOTTOM); a=rf.getchannel('A').point(lambda v:int(v*refl))
    g=Image.linear_gradient('L').resize(rf.size).point(lambda v:255-v); a=ImageChops.multiply(a,g); rf.putalpha(a)
    scene.alpha_composite(rf.filter(ImageFilter.GaussianBlur(3)),(x,bottom))
    scene.alpha_composite(dv,(x,y))
s1=cutout(K+'s1.png'); node=cutout(K+'node.png'); touch=cutout(K+'touch.png')
place(touch,600,500,1058,refl=.08)
place(s1,800,1150,1110)
place(node,300,1760,1075)
img=scene.convert('RGB')
# varm fargetone, vignett og korn
img=ImageEnhance.Color(img).enhance(1.06); img=ImageEnhance.Contrast(img).enhance(1.04)
vg=Image.new('L',(W,H),0); ImageDraw.Draw(vg).ellipse([-W*.25,-H*.3,W*1.25,H*1.3],fill=255); vg=vg.filter(ImageFilter.GaussianBlur(260))
img=Image.composite(img,Image.new('RGB',(W,H),(40,30,22)),vg.point(lambda v:int(150+v*105/255)))
gn=Image.effect_noise((W,H),18).convert('RGB'); img=Image.blend(img,ImageChops.overlay(img,gn),0.18)
img=img.crop((0,0,W,H)).resize((1000,700),Image.LANCZOS)
A=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'images')
for n, sz in (('xlarge', (1000, 700)), ('large', (500, 350)), ('small', (250, 175))):
    img.resize(sz, Image.LANCZOS).save(os.path.join(A, n + '.png'), optimize=True)
