"""Raster variants of SIPAK's existing document and shield mark."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]/'public'
NAVY='#25285f'
SVG='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#25285f"/><g fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M32 10H17a3 3 0 0 0-3 3v35a3 3 0 0 0 3 3h23a3 3 0 0 0 3-3V21Z"/><path d="M32 10v11h11M22 29h12M22 36h10M22 43h6"/></g><path d="m44 31 10 5v8c0 6-6 10-10 12-4-2-10-6-10-12v-8z" fill="#25285f" stroke="white" stroke-width="2.6" stroke-linejoin="round"/><path d="m39 43 4 4 6-7" fill="none" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'''

def icon(size,maskable=False):
    scale=16;image=Image.new('RGB',(64*scale,64*scale),NAVY);draw=ImageDraw.Draw(image)
    def points(values):return [(round(x*scale),round(y*scale)) for x,y in values]
    def line(values,width=2.8):draw.line(points(values),fill='white',width=round(width*scale),joint='curve')
    line([(32,10),(17,10),(14,13),(14,48),(17,51),(40,51),(43,48),(43,21),(32,10)])
    line([(32,10),(32,21),(43,21)])
    for y,end in [(29,34),(36,32),(43,28)]:line([(22,y),(end,y)])
    shield=[(44,31),(54,36),(54,44),(52,49),(48,53),(44,56),(40,53),(36,49),(34,44),(34,36),(44,31)]
    draw.polygon(points(shield),fill=NAVY);line(shield,2.6);line([(39,43),(43,47),(49,40)],2.6)
    if maskable:
        small=image.resize((round(64*scale*.88),)*2,Image.Resampling.LANCZOS)
        image=Image.new('RGB',image.size,NAVY);image.paste(small,((image.width-small.width)//2,(image.height-small.height)//2))
    return image.resize((size,size),Image.Resampling.LANCZOS)

if __name__=='__main__':
    (ROOT/'icons').mkdir(parents=True,exist_ok=True)
    (ROOT/'favicon.svg').write_text(SVG,encoding='utf-8')
    for size in (192,512):icon(size).save(ROOT/'icons'/f'sipak-{size}.png')
    icon(512,True).save(ROOT/'icons'/'sipak-maskable-512.png')
    icon(180).save(ROOT/'apple-touch-icon.png')
    icon(64).save(ROOT/'favicon.ico',sizes=[(16,16),(32,32),(48,48)])
