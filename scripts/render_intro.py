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
 scale=.72*mix(.94,1,intro)
 key='final' if t>=2.98 else None
 if key in cache:return cache[key]
 scene=base.copy();scene.alpha_composite(gavel.rotate(-angle_at(t),Image.Resampling.BICUBIC,center=(1060*S,500*S)))
 scene=scene.resize((round(1400*scale),round(900*scale)),Image.Resampling.LANCZOS)
 if intro<1:scene.putalpha(scene.getchannel('A').point(lambda v:round(v*intro)))
 pos=(round(W/2-790*scale),round(H/2-570*scale))
 if key:cache[key]=(scene,pos)
 return scene,pos
def frame(t,fade=True):
 image=Image.new('RGBA',(W,H),NAVY+(255,));scene,pos=scene_at(t);image.alpha_composite(scene,pos)
 if fade and t>4.42:
  cover=Image.new('RGBA',image.size,NAVY+(round(255*ease((t-4.42)/.75)),));image.alpha_composite(cover)
 return image.convert('RGB')
def sound():
 rate=48000;count=round(rate*DURATION);rng=random.Random(9222)
 dry=[0.0]*count
 # A short contact crack and fixed, rapidly decaying wood modes: no bass drop.
 for hit,gain,tuning in [(1.38,.98,1.015),(1.93,1.0,1.0)]:
  start=round(hit*rate);low=0.0
  modes=[(217,.48,31),(463,.31,39),(927,.19,54),(1843,.105,82),(2921,.045,110)]
  for j in range(round(.42*rate)):
   k=start+j
   if k>=count:break
   t=j/rate;noise=rng.uniform(-1,1);low=.55*low+.45*noise
   contact=(.72*(noise-low)*math.exp(-t*240)+.3*low*math.exp(-t*77))
   wood=sum(level*math.sin(2*math.pi*hz*tuning*t)*math.exp(-t*decay) for hz,level,decay in modes)
   body=.09*math.sin(2*math.pi*118*t)*math.exp(-t*34)
   dry[k]+=gain*(1-math.exp(-t*4500))*(contact+wood+body)
 channels=[]
 for side in range(2):
  track=dry.copy()
  # Asymmetric room reflections make the echo read as space, not a repeated hit.
  for delay,amount in ([(.047,.19),(.137,.24),(.278,.115),(.438,.065)] if side==0 else [(.071,.18),(.183,.22),(.329,.12),(.493,.06)]):
   offset=round(delay*rate);filtered=0.0
   for k in range(count-offset):
    filtered=.62*filtered+.38*dry[k]
    track[k+offset]+=filtered*amount
  # Parallel damped combs provide a diffuse room tail behind the distinct echoes.
  for delay,feedback in ([(.031,.72),(.037,.74),(.041,.71),(.053,.73)] if side==0 else [(.033,.73),(.039,.71),(.047,.74),(.059,.72)]):
   size=round(delay*rate);buffer=[0.0]*size;filtered=0.0;predelay=round(.035*rate)
   for k in range(count):
    index=k%size;old=buffer[index];filtered=.57*filtered+.43*old
    buffer[index]=(dry[k-predelay] if k>=predelay else 0)+filtered*feedback
    track[k]+=.065*old
  channels.append(track)
 peak=max(max(map(abs,c)) for c in channels);gain=.76/peak
 pcm=array.array('h')
 for i in range(count):
  fade=1-ease((i/rate-4.3)/.75)
  for side in range(2):pcm.append(round(channels[side][i]*gain*fade*32767))
 target=ROOT/'sipak-intro-white-sfx.wav'
 with wave.open(str(target),'wb') as wav:wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm.tobytes())
 return target
if __name__=='__main__':
 audio=sound();output=ROOT/'sipak-intro-white-1080p.mp4'
 if '--audio-only' in sys.argv:
  import shutil
  if not output.exists():raise SystemExit('Create the full video first.')
  for target in [output,ROOT/'sipak-intro-white-web.mp4']:
   temporary=target.with_name(target.stem+'-remux.mp4')
   subprocess.run([FFMPEG,'-y','-i',str(target),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(temporary)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   temporary.replace(target)
  shutil.copy2(ROOT/'sipak-intro-white-web.mp4',ROOT.parents[1]/'public'/'intro'/'sipak-intro.mp4')
  print('Updated stereo wood impact, room reflections and echo. Video frames unchanged.',flush=True)
  raise SystemExit(0)
 frame(1.38).save(ROOT/'impact.jpg',quality=94);frame(4,False).crop((420,0,1500,1080)).resize((720,720),Image.Resampling.LANCZOS).save(ROOT/'poster.jpg',quality=94)
 cmd=[FFMPEG,'-y','-f','rawvideo','-vcodec','rawvideo','-s',f'{W}x{H}','-pix_fmt','rgb24','-r',str(FPS),'-i','-','-i',str(audio),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(output)]
 with (ROOT/'encoding.log').open('w') as log:
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
  for i in range(round(FPS*DURATION)):
   p.stdin.write(frame(i/FPS).tobytes())
   if i%30==0:print(f'Rendered {i}/156',flush=True)
  p.stdin.close();result=p.wait()
 if result:raise SystemExit('Encoding failed')
 web=ROOT/'sipak-intro-white-web.mp4'
 subprocess.run([FFMPEG,'-y','-i',str(output),'-vf','crop=1080:1080:420:0,scale=720:720','-c:v','libx264','-crf','23','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(web)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 import shutil
 target=ROOT.parents[1]/'public'/'intro';target.mkdir(parents=True,exist_ok=True)
 shutil.copy2(web,target/'sipak-intro.mp4');shutil.copy2(ROOT/'poster.jpg',target/'poster.jpg')
 print(f'Finished; 1080p {output.stat().st_size} bytes, web {web.stat().st_size} bytes.',flush=True)
