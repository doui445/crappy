#coding: utf-8
from __future__ import print_function, division

## @addtogroup technical
# @{

## @defgroup cameraConfig cameraConfig
# @{
# @brief The class used to initialize cameras
# @author Victor Couty
# @version 0.2
# @date 15/03/2017

import Tkinter as tk
from PIL import ImageTk,Image
from time import time
import cv2
import numpy as np
from multiprocessing import Process,Pipe

class Hist_generator(Process):
  """
  Process to generate the histogram of images

  It only takes a Pipe at init, all the data will be transferred through it.
  See self.run docstring for more infos
  """
  def __init__(self,pipe):
    Process.__init__(self)
    self.pipe = pipe

  def run(self):
    """Expects a tuple of 3 args through the pipe:
        - out_size: Tuple, The dimensions of the output histogram image
        - hist_range: Tuple, The lower and upper value of the histogram
          (eg: (0,256) for full scale uint8)
        - img: A numpy array with the image,
          if not single channel, it will be converted to a single channel
    """
    while True:
      out_size,hist_range,img = self.pipe.recv()
      if not isinstance(out_size,tuple):
        break
      hist_range = hist_range[0],hist_range[1]+1
      #np.histogram removes 1 value to the output array, no idea why...
      if len(img.shape) == 3:
        img = np.mean(img,axis=2)
      assert len(img.shape) == 2,"Invalid image: shape= "+str(img.shape)
      h = np.histogram(img,bins=np.arange(*hist_range))[0]# The actual histogram
      x = np.arange(out_size[1])# The base of the image
      # We need to interpolate the histogram on the size of the output image
      l = hist_range[1]-hist_range[0]-1
      fx = np.arange(0,out_size[1],out_size[1]/l,dtype=np.float)
      #fx *= out_size[1]/len(fx)
      h2 = np.interp(x,fx,h)
      h2 *= out_size[0]/h2.max()

      out_img = np.zeros(out_size)
      for i in range(out_size[1]):
        out_img[0:int(out_size[0]-h2[i]),i] = 255
      self.pipe.send(out_img)

class Camera_config(object):
  """
  Class creating a graphical interface to configure a camera

  It will launch create the window  when instanciated:
  just call Cam_config(camera)

  It takes a single arg: the camera class
  (it must inherit from crappy.sensor._meta.MasterCam)
  """
  def __init__(self,camera):
    self.camera = camera
    self.label_shape = 800,600
    self.scale_length = 350
    self.root = tk.Tk()
    self.root.protocol("WM_DELETE_WINDOW",self.stop)
    self.zoom_step = .1
    self.reset_zoom()
    self.img = self.camera.read_image()[1]
    self.on_resize()
    self.convert_img()
    self.create_window()
    self.update_img()
    self.start_histogram()
    self.update_histogram()
    self.refresh_rate = 1/50
    self.low = 0
    self.high = 255
    self.t = time()
    self.t_fps = self.t
    self.go = True
    self.main()

  def stop(self):
    self.hist_pipe.send((0,0,0))
    self.hist_pipe.recv()
    self.hist_process.join()
    self.go = False
    self.root.destroy()

  def start_histogram(self):
    self.hist_pipe,self.p2 = Pipe()
    self.hist_process = Hist_generator(self.p2)
    self.hist_process.start()
    self.hist_pipe.send(((80,self.label_shape[1]),(0,256),self.img))

# ============ Initialization of the tkinter window and widgets ============
  def create_window(self):
    self.root.grid_rowconfigure(1,weight=1)
    self.root.grid_columnconfigure(0,weight=1)
    self.img_label = tk.Label(self.root)
    self.img_label.configure(image=self.c_img)
    self.hist_label = tk.Label(self.root)
    self.hist_label.grid(row=0,column=0)
    #self.img_label.pack(fill=tk.BOTH)
    self.img_label.grid(row=1,column=0,rowspan=len(self.camera.settings_dict)+2,
        sticky=tk.N+tk.E+tk.S+tk.W)
    self.create_inputs()
    self.create_infos()
    self.img_label.bind('<4>', self.zoom_in)
    self.img_label.bind('<5>', self.zoom_out)
    self.root.bind('<MouseWheel>', self.zoom)
    self.img_label.bind('<1>', self.start_move)
    self.img_label.bind('<B1-Motion>', self.move)

  def create_inputs(self):
    settings = self.camera.settings_dict.keys()
    settings.sort(key=lambda e: type(self.camera.settings[e].limits))
    self.scales = {}
    self.radios = {}
    self.checks = {}
    for i,k in enumerate(settings):
      s = self.camera.settings[k]
      if type(s.limits) == tuple:
        self.create_scale(s,i)
      elif type(s.limits) == bool:
        self.create_check(s,i)
      elif type(s.limits) == dict:
        self.create_radio(s,i)
    self.apply_button = tk.Button(self.root,text="Apply",
                                  command=self.apply_settings)
    self.apply_button.grid(column=1,row=i+3)

  def create_infos(self):
    self.info_frame = tk.Frame()
    self.info_frame.grid(row=0,column=1)
    self.fps_label = tk.Label(self.info_frame,text="fps:")
    self.fps_label.pack()
    self.auto_range = tk.IntVar()
    self.range_check = tk.Checkbutton(self.info_frame,
                      text="Auto range",variable=self.auto_range)
    self.range_check.pack()
    self.minmax_label = tk.Label(self.info_frame,text="min: max:")
    self.minmax_label.pack()
    self.range_label = tk.Label(self.info_frame,text="range:")
    self.range_label.pack()
    self.bits_label = tk.Label(self.info_frame,text="detected bits:")
    self.bits_label.pack()
    self.zoom_label = tk.Label(self.info_frame,text="Zoom: 100%")
    self.zoom_label.pack()

  def create_scale(self,setting,pos):
    f = tk.Frame(self.root)
    f.grid(row=pos+2,column=1,sticky=tk.E+tk.W)
    if type(setting.limits[0]) is float:
      step = (setting.limits[1]-setting.limits[0])/1000
    else:
      step = 1 # To go through all possible int values
    tk.Label(f,text=setting.name).pack()
    self.scales[setting.name] = tk.Scale(f,orient='horizontal', resolution=step,
        length=self.scale_length,from_=setting.limits[0],to=setting.limits[1])
    self.scales[setting.name].pack()
    self.scales[setting.name].set(setting.value)

  def create_radio(self,setting,pos):
    self.radios[setting.name] = tk.IntVar()
    f = tk.Frame(self.root)
    f.grid(row=pos+2,column=1,sticky=tk.E+tk.W)
    tk.Label(f,text=setting.name+":").pack(anchor=tk.W)
    for k,v in setting.limits.iteritems():
      r = tk.Radiobutton(f, text=k, variable=self.radios[setting.name], value=v)
      if setting.value == v:
        r.select()
      r.pack(anchor=tk.W)

  def create_check(self,setting,pos):
    self.checks[setting.name] = tk.IntVar()
    f = tk.Frame(self.root)
    f.grid(row=pos+2,column=1,sticky=tk.E+tk.W)
    b = tk.Checkbutton(f, text=setting.name,variable=self.checks[setting.name])
    if setting.value:
      b.select()
    b.pack(anchor=tk.W)

# ============ Tools ==============

  def detect_bits(self):
    b = 8
    o = 256
    m = self.img.max()
    while o < m:
      b+=1
      o*=2
    return b

  def get_label_shape(self):
    r = self.img_label.winfo_height()-2,self.img_label.winfo_width()-2
    return r

  def resized(self):
    """Returns True if window has been resized and saves the new coordinates"""
    new = self.get_label_shape()
    # Integer rounding can lead to resizing loop if we compare exact values
    # so let's resize only if the difference is signigficant (more than 2pix)
    #if new != self.label_shape:
    if sum([abs(i-j) for i,j in zip(new,self.label_shape)]) >= 5:
      if new[0] > 0 and new[1] > 0:
        self.label_shape = new
      return True
    return False

  def convert_img(self):
    """Converts the image to uint if necessary, then to a PhotoImage"""
    if len(self.img.shape) == 3:
      self.img = self.img[:,:,::-1] # BGR to RGB
    if self.img.dtype != np.uint8:
      #if self.auto_range.get():
      #Ok, this is not a very clean way, but at first auto_range is not defined
      try:
        assert self.auto_range.get()
        # ar=True, 16bits
        self.low = np.percentile(self.img,1)
        self.high = np.percentile(self.img,99)
        self.img8 = ((np.clip(self.img,self.low,self.high)
                    -self.low)*256/self.high).astype(np.uint8)
      except (AssertionError,AttributeError):
        # ar=False, 16 bits
        self.img8 = (self.img/2**(self.detect_bits()-8)).astype(np.uint8)
    else:
      try:
        assert self.auto_range.get()
        # ar=True, 8bits
        self.low = np.percentile(self.img,1)
        self.high = np.percentile(self.img,99)
        self.img8 = ((np.clip(self.img,self.low,self.high)
                        -self.low)*256/self.high)
      except (AssertionError,AttributeError):
        # ar=False, 8bits
        self.img8 = self.img
    slx = slice(int(self.img.shape[0]*self.zoom_window[0]),
        int(self.img.shape[0]*self.zoom_window[2]))
    sly = slice(int(self.img.shape[1]*self.zoom_window[1]),
        int(self.img.shape[1]*self.zoom_window[3]))
    self.c_img = ImageTk.PhotoImage(Image.fromarray(
        cv2.resize(self.img8[slx,sly],tuple(reversed(self.img_shape)),
        interpolation=0)))
    # Interpolation=0 means nearest neighbor
    # Resize somehow takes x,y when EVERYTHING else takes y,x thanks numpy !

# =============== Update functions ===============

  def update_histogram(self):
    while not self.hist_pipe.poll():
      pass
    h = self.hist_pipe.recv()
    if self.auto_range.get():
      lo = int(self.low/2**self.detect_bits()*h.shape[1])
      hi = int(self.high/2**self.detect_bits()*h.shape[1])
      if lo < h.shape[1]:
        h[:,lo] = 127
      if hi < h.shape[1]:
        h[:,hi] = 127
    self.hist = ImageTk.PhotoImage(Image.fromarray(h))
    self.hist_label.configure(image=self.hist)
    self.hist_pipe.send(((80,self.label_shape[1]),(0,2**self.detect_bits()),
      self.img))

  def update_img(self):
    self.convert_img()
    self.img_label.configure(image=self.c_img)

  def update_infos(self):
    self.minmax_label.configure(text="min: {} max: {}".format(self.img.min(),
                                                        self.img.max()))
    self.bits_label.configure(text="detected bits: {} ({} values)".format(
      self.detect_bits(),2**self.detect_bits()))
    self.range_label.configure(text='Range: {}-{}'.format(self.low,self.high))

# ============ Zoom related methods ===============

  def reset_zoom(self):
    self.zoom_level = 1
    self.zoom_window = (0,0,1,1)

  def make_new_window(self,ey,ex):
    """
    Hang on, it is not that complicated: given the location of the zoom event
    this will compute the new zoom window. It is represented by 4 floats
    between 0 and 1 miny,minx,maxy,maxx, default is 0,0,1,1
    """
    # The zoom factor (%)
    z = (1+self.zoom_step)**self.zoom_level
    self.zoom_label.configure(text="Zoom: %.1f%%"%(100*z))
    # The previous values are used to compute the actual displacement
    pminy,pminx,pmaxy,pmaxx = self.zoom_window
    # Make the event position global (we get the position on the label itself)
    ex *= self.label_shape[1]/self.img_shape[1]
    ex -= (self.label_shape[1]-self.img_shape[1])/(2*self.img_shape[1])
    # ex is now somewhere between 0 and 1, reflecting abciss on the image
    # Last edit: cast it on the whole image, taking zoom in account
    ex = ex*(pmaxx-pminx)+pminx
    # Now ex*img.shape[1] would be the coordinate of the pixel
    # Where it is located on the picture, relatively to the previous window
    rx = (ex-pminx)/(pmaxx-pminx)
    # And now we can compute the new window abciss
    minx = ex-rx/z
    maxx = 1/z+minx
    # Exactly the same procedure for y:
    ey *= self.label_shape[0]/self.img_shape[0]
    ey -= (self.label_shape[0]-self.img_shape[0])/(2*self.img_shape[0])
    ey = ey*(pmaxy-pminy)+pminy
    ry = (ey-pminy)/(pmaxy-pminy)
    miny = ey-ry/z
    maxy = 1/z+miny
    # Warp if we are zooming out of the image
    if minx < 0:
      minx = 0
      maxx = 1/z
    if miny < 0:
      miny = 0
      maxy = 1/z
    if maxx > 1:
      maxx = 1
      minx = 1-1/z
    if maxy > 1:
      maxy = 1
      miny = 1-1/z
    self.zoom_window = (miny,minx,maxy,maxx)


  def move_window(self,y,x):
    """Given the movement of the mouse, it will recompute the zoom_window"""
    z = (1+self.zoom_step)**self.zoom_level
    miny = self.previous_window[0]+y/z
    maxy = self.previous_window[2]+y/z
    minx = self.previous_window[1]+x/z
    maxx = self.previous_window[3]+x/z
    if minx < 0:
      minx = 0
      maxx = 1/z
    if miny < 0:
      miny = 0
      maxy = 1/z
    if maxx > 1:
      maxx = 1
      minx = 1-1/z
    if maxy > 1:
      maxy = 1
      miny = 1-1/z
    self.zoom_window = (miny,minx,maxy,maxx)

# ========== Callback functions ===========

  def apply_settings(self):
    """Callback for the apply button
    as its name suggests, it will apply all the edited settings"""
    # Applying scales values to the camera
    for name,scale in self.scales.iteritems():
      if self.camera.settings[name].value != scale.get():
        self.camera.settings[name].value = scale.get()
    # Applying checks (boolean values)
    for name,value in self.checks.iteritems():
      if bool(self.camera.settings[name].value) != bool(value.get()):
        self.camera.settings[name].value = bool(value.get())
    # And applying the radios (selectable values)
    for name,value in self.radios.iteritems():
      if self.camera.settings[name].value != value.get():
        self.camera.settings[name].value = value.get()
    # READING from the camera to move the scales to the actual values
    for name,scale in self.scales.iteritems():
      if self.camera.settings[name].value != scale.get():
        scale.set(self.camera.settings[name].value)
    # Updating the window
    self.img = self.camera.read_image()[1]
    self.update_img()
    self.on_resize()

  def on_resize(self):
    """Recomputes the new shape of the resized image"""
    ratio = min(self.label_shape[0]/self.img.shape[0],
            self.label_shape[1]/self.img.shape[1])
    self.img_shape = (int(self.img.shape[0]*ratio),int(self.img.shape[1]*ratio))

  def zoom(self,event):
    """For windows, only one type of wheel event"""
    #This event is relative to the window!
    event.y -= self.img_label.winfo_y()
    if event.num == 5 or event.delta < 0:
      self.zoom_out(event)
    elif event.num == 4 or event.delta > 0:
      self.zoom_in(event)

  def zoom_in(self,event):
    """Called when scrolling in"""
    self.zoom_level += 1
    ls = self.get_label_shape()
    self.make_new_window(event.y/ls[0],event.x/ls[1])

  def zoom_out(self,event):
    """Called when scrolling out"""
    if self.zoom_level == 0:
      return
    elif self.zoom_level < 0:
      self.zoom_level = 0
    else:
      self.zoom_level -= 1
    ls = self.get_label_shape()
    self.make_new_window(event.y/ls[0],event.x/ls[1])

  def start_move(self,event):
    """To save the coordinates before actually moving"""
    self.mv_start = (event.y,event.x)
    self.previous_window = self.zoom_window

  def move(self,event):
    """Moving the image when dragging it with the mouse"""
    mvy = (self.mv_start[0]-event.y)/self.img_shape[0]
    mvx = (self.mv_start[1]-event.x)/self.img_shape[1]
    self.move_window(mvy,mvx)

# ============ And finally, the main loop ===========

  def main(self):
    loop = 0
    while self.go:
      loop += 1 # For the fps counter
      self.img = self.camera.read_image()[1]
      curr_t = time()
      if curr_t - self.t >= self.refresh_rate:
        # Time to refresh the window
        if curr_t - self.t_fps > .5:
          # Time to update the fps
          self.fps_label.configure(text="fps=%.1f"%(loop/(curr_t-self.t_fps)))
          self.t_fps = curr_t
          loop = 0
        if self.hist_pipe.poll():
          # The histogram proccess has finished computing: let's update
          self.update_histogram()
        self.update_img()
        self.update_infos()
        self.t = curr_t
      if self.resized():
        # Even if it is not time to update, the window has been resized
        self.on_resize()
        self.update_img()
      self.root.update()
    print("Camera config done !")

#@}
#@}
