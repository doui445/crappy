# coding: utf-8

import time
from ximea import xiapi

from .camera import Camera


class Xiapi(Camera):
  """
  Camera class for ximeas using official XiAPI
  """
  def __init__(self):
    Camera.__init__(self)
    self.name = "Xiapi"
    self.cam = xiapi.Camera()
    self.img = xiapi.Image()
    self.add_setting("width",self._get_w,self._set_w,(1,self._get_w))
    self.add_setting("height",self._get_h,self._set_h,(1,self._get_h))
    self.add_setting("xoffset",self._get_ox,self._set_ox,(0,self._get_w))
    self.add_setting("yoffset",self._get_oy,self._set_oy,(0,self._get_h))
    self.add_setting("exposure",self._get_exp,self._set_exp,(28,500000),10000)
    self.add_setting("gain",self._get_gain,self._set_gain,(0.,6.))
    self.add_setting("AEAG",self._get_AEAG,self._set_AEAG,True,False)
    self.add_setting("external_trig",self._get_extt,self._set_extt,True,False)

  def _get_w(self):
    return self.cam.get_width()

  def _get_h(self):
    return self.cam.get_height()

  def _get_ox(self):
    return self.cam.get_offsetX()

  def _get_oy(self):
    return self.cam.get_offsetY()

  def _get_gain(self):
    return self.cam.get_gain()

  def _get_exp(self):
    return self.cam.get_exposure()

  def _get_AEAG(self):
    return self.cam.get_param('aeag')

  def _get_extt(self):
    r = self.cam.get_trigger_source()
    if r == 'XI_TRG_OFF':
      return False
    else:
      return True

  def _set_w(self,i):
    self.cam.set_width(i)

  def _set_h(self,i):
    self.cam.set_height(i)

  def _set_ox(self,i):
    self.cam.set_offsetX(i)

  def _set_oy(self,i):
    self.cam.set_offsetY(i)

  def _set_gain(self,i):
    self.cam.set_gain(i)

  def _set_exp(self,i):
    self.cam.set_exposure(i)

  def _set_AEAG(self,i):
    self.cam.set_param('aeag',int(i))

  def _set_extt(self,i):
    self.cam.stop_acquisition()
    if i:
      self.cam.set_gpi_mode('XI_GPI_TRIGGER')
      self.cam.set_trigger_source('XI_TRG_EDGE_RISING')
    else:
      self.cam.set_gpi_mode('XI_GPI_OFF')
      self.cam.set_trigger_source('XI_TRG_OFF')
    self.cam.start_acquisition()

  def open(self,sn=None,**kwargs):
    """
    Will actually open the camera, args will be set to default unless
    specified otherwise in kwargs

    If sn is given, it will open the camera with
    the corresponing serial number

    Else, it will open any camera
    """
    self.sn = sn
    #self.close()
    if self.sn is not None:
      self.cam.open_device_by_SN(self.sn)
    else:
      self.cam.open_device()

    for k in kwargs:
      assert k in self.available_settings,str(self)+"Unexpected kwarg: "+str(k)
    self.set_all(**kwargs)
    self.set_all(**kwargs)
    self.cam.start_acquisition()

  def reopen(self,**kwargs):
    """
    Will reopen the camera, args will be set to default unless
    specified otherwise in kwargs
    """
    self.open()
    self.set_all(override=True,**kwargs)

  def get_image(self):
    """
    This method get a frame on the selected camera and return a ndarray

    Returns:
        frame from ximea device (ndarray height*width)
    """
    self.cam.get_image(self.img)
    t = time.time()
    return t,self.img.get_image_data_numpy()

  def close(self):
    """
    This method closes properly the camera

    Returns:
        void return function.
    """
    self.cam.close_device()
