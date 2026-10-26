"""Offline-only motion interpolation. Build dependencies are not on app sys.path."""
from pathlib import Path
import sys
root=Path(__file__).parent
sys.path.insert(0,str(root/'.asset-build-tools'))
import cv2
import numpy as np
cv2.setNumThreads(2)
ACTIONS=('heart_finger','heart_chest','heart_overhead')
STEPS=8

def gray(im):
 alpha=im[:,:,3:4].astype(np.float32)/255
 rgb=im[:,:,:3]*alpha+245*(1-alpha)
 return cv2.cvtColor(rgb.astype(np.uint8),cv2.COLOR_BGR2GRAY)

def premultiply(im):
 out=im.astype(np.float32)/255
 out[:,:,:3]*=out[:,:,3:4]
 return out

def morph(a,b,f,g,t,grid):
 ma=grid-t*f;mb=grid-(1-t)*g
 for _ in range(2):
  ma=grid-t*cv2.remap(f,ma,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
  mb=grid-(1-t)*cv2.remap(g,mb,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
 wa=cv2.remap(a,ma,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
 wb=cv2.remap(b,mb,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
 out=wa*(1-t)+wb*t
 out[:,:,:3]/=np.maximum(out[:,:,3:4],.00001)
 return np.clip(out*255+.5,0,255).astype(np.uint8)

def build():
 for name in ACTIONS:
  source=root/'sprites-anime/prepared/306/heart-smooth'/name
  images=[cv2.imdecode(np.frombuffer((source/f'{i}.png').read_bytes(),dtype=np.uint8),cv2.IMREAD_UNCHANGED) for i in range(6)]
  if any(im is None for im in images): raise RuntimeError('Missing keyframes')
  h,w=images[0].shape[:2]
  x,y=np.meshgrid(np.arange(w,dtype=np.float32),np.arange(h,dtype=np.float32));grid=np.stack((x,y),axis=-1)
  def write(im,index):
   for height in (119,187,238,306):
    dest=root/'sprites-anime/prepared'/str(height)/'heart-motion'/name
    dest.mkdir(parents=True,exist_ok=True)
    resized=im if height==306 else cv2.resize(im,(round(height*1.05),height),interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode('.png',resized)
    if not ok: raise RuntimeError('Write failed')
    (dest/f'{index}.png').write_bytes(encoded.tobytes())
  for i in range(5):
   dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
   f=dis.calc(gray(images[i]),gray(images[i+1]),None)
   g=dis.calc(gray(images[i+1]),gray(images[i]),None)
   a,b=premultiply(images[i]),premultiply(images[i+1])
   for step in range(STEPS):
    write(images[i] if step==0 else morph(a,b,f,g,step/STEPS,grid),i*STEPS+step)
  write(images[-1],5*STEPS)
  print(name, '41 disk frames; no optical flow runs in the pet',flush=True)
if __name__=='__main__': build()
