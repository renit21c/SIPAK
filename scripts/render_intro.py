from pathlib import Path
import array,math,random,subprocess,sys,wave
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]/'artifacts'/'sipak-intro-white'
ROOT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT.parents[1]/'tmp'/'intro-tools'))
import imageio_ffmpeg
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
W,H,FPS,DURATION,S=1920,1080,30,5.2,2
NAVY=(37,40,95);WHITE=(255,255,255)
def clamp(x):return max(0,min(1,x))
def ease(x):x=clamp(x);return x*x*(3-2*x)
def out(x):return 1-(1-clamp(x))**3
def mix(a,b,t):return a+(b-a)*t
def rect(v):return tuple(round(x*S) for x in v)
def pts(v):return [(round(x*S),round(y*S)) for x,y in v]
gavel=Image.new('RGBA',(1400*S,900*S));d=ImageDraw.Draw(gavel)
d.line(pts([(742,391),(1060,500)]),fill=WHITE,width=36*S)
d.ellipse(rect((1042,482,1078,518)),fill=WHITE)
d.rounded_rectangle(rect((646,270,798,526)),radius=12*S,fill=WHITE)
d.rounded_rectangle(rect((622,249,822,285)),radius=10*S,fill=WHITE)
d.rounded_rectangle(rect((622,510,822,546)),radius=10*S,fill=WHITE)
base=Image.new('RGBA',gavel.size);bd=ImageDraw.Draw(base)
bd.rounded_rectangle(rect((505,724,935,765)),radius=14*S,fill=WHITE)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',145)
small=ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf',26)
def tracked(draw,text,y,font,spacing,fill):
 widths=[draw.textlength(ch,font=font) for ch in text];x=(W-sum(widths)-spacing*(len(text)-1))/2
 for ch,width in zip(text,widths):draw.text((round(x),round(y)),ch,font=font,fill=fill,anchor='lt');x+=width+spacing
def angle_at(t):
 keys=[(0,5),(.55,5),(.97,22),(1.16,25),(1.38,-23),(1.5,-15),(1.64,-21),(1.79,11),(1.93,-23),(2.05,-17),(2.22,-23),(5.2,-23)]
 for (ta,a),(tb,b) in zip(keys,keys[1:]):
  if ta<=t<=tb:return mix(a,b,ease((t-ta)/(tb-ta)))
 return -23
cache={}
def scene_at(t):
 intro=out((t-.12)/.7);settle=ease((t-2.23)/.75)
 scale=mix(1.12,.67,settle)*mix(.94,1,intro)
 key='final' if t>=2.98 else None
 if key in cache:return cache[key]
 scene=base.copy();scene.alpha_composite(gavel.rotate(-angle_at(t),Image.Resampling.BICUBIC,center=(1060*S,500*S)))
 scene=scene.resize((round(1400*scale),round(900*scale)),Image.Resampling.LANCZOS)
 if intro<1:scene.putalpha(scene.getchannel('A').point(lambda v:round(v*intro)))
 pos=(round((W-scene.width)/2),round(mix(-35,5,settle)+mix(22,0,intro)))
 if key:cache[key]=(scene,pos)
 return scene,pos
def frame(t,fade=True):
 image=Image.new('RGBA',(W,H),NAVY+(255,));scene,pos=scene_at(t);image.alpha_composite(scene,pos)
 title=out((t-2.68)/.65)
 if title:
  layer=Image.new('RGBA',image.size);ld=ImageDraw.Draw(layer)
  tracked(ld,'SIPAK',mix(688,655,title),font,19,WHITE+(round(255*title),))
  tracked(ld,'KOMISI DISIPLIN',838,small,7,(216,220,240,round(220*ease((t-3.1)/.55))))
  image.alpha_composite(layer)
 if fade and t>4.42:
  cover=Image.new('RGBA',image.size,NAVY+(round(255*ease((t-4.42)/.75)),));image.alpha_composite(cover)
 return image.convert('RGB')
def sound():
 rate=48000;count=round(rate*DURATION);samples=[0.0]*count;rng=random.Random(9221)
 # Lower resonances, a firmer transient and a darker room tail.
 for hit,gain in [(1.38,.94),(1.93,1.0)]:
  start=round(hit*rate);low=0.0
  for j in range(round(1.25*rate)):
   k=start+j
   if k>=count:break
   t=j/rate;noise=rng.uniform(-1,1);low=.68*low+.32*noise
   attack=1-math.exp(-t*2100)
   transient=.8*low*math.exp(-t*100)
   pitch=58+48*math.exp(-t*29)
   body=.52*math.sin(2*math.pi*pitch*t)*math.exp(-t*9)+.26*math.sin(2*math.pi*151*t)*math.exp(-t*17)
   wood=.20*math.sin(2*math.pi*376*t)*math.exp(-t*26)+.07*math.sin(2*math.pi*1109*t)*math.exp(-t*51)
   value=gain*attack*(transient+body+wood)
   samples[k]+=value
   for delay,amount in [(.043,.21),(.087,.14),(.141,.095),(.213,.055),(.307,.03)]:
    dest=k+round(delay*rate)
    if dest<count:samples[dest]+=value*amount
 # Restrained, low cinematic rise leading into the second knock.
 for k in range(round(.55*rate),round(2.25*rate)):
  t=k/rate;envelope=math.sin(math.pi*clamp((t-.55)/1.7))**2
  samples[k]+=.038*envelope*(math.sin(2*math.pi*43*t)+.5*math.sin(2*math.pi*65*t))
 for k in range(round(2.45*rate),count):
  t=k/rate-2.45
  samples[k]+=.023*(1-math.exp(-t*10))*math.exp(-t*2)*(math.sin(2*math.pi*130.81*t)+.45*math.sin(2*math.pi*196*t))
 peak=max(map(abs,samples));gain=.78/peak
 pcm=array.array('h',(round(v*gain*32767*(1-ease((i/rate-4.35)/.7))) for i,v in enumerate(samples)))
 target=ROOT/'sipak-intro-white-sfx.wav'
 with wave.open(str(target),'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm.tobytes())
 return target
if __name__=='__main__':
 audio=sound();output=ROOT/'sipak-intro-white-1080p.mp4'
 frame(1.38).save(ROOT/'impact.jpg',quality=94);frame(4,False).save(ROOT/'poster.jpg',quality=94)
 cmd=[FFMPEG,'-y','-f','rawvideo','-vcodec','rawvideo','-s',f'{W}x{H}','-pix_fmt','rgb24','-r',str(FPS),'-i','-','-i',str(audio),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(output)]
 with (ROOT/'encoding.log').open('w') as log:
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
  for i in range(round(FPS*DURATION)):
   p.stdin.write(frame(i/FPS).tobytes())
   if i%30==0:print(f'Rendered {i}/156',flush=True)
  p.stdin.close();result=p.wait()
 if result:raise SystemExit('Encoding failed')
 web=ROOT/'sipak-intro-white-web.mp4'
 subprocess.run([FFMPEG,'-y','-i',str(output),'-vf','scale=1280:720','-c:v','libx264','-crf','23','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(web)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 import shutil
 target=ROOT.parents[1]/'public'/'intro';target.mkdir(parents=True,exist_ok=True)
 shutil.copy2(web,target/'sipak-intro.mp4');shutil.copy2(ROOT/'poster.jpg',target/'poster.jpg')
 print(f'Finished; 1080p {output.stat().st_size} bytes, web {web.stat().st_size} bytes.',flush=True)
