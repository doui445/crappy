﻿from _meta import MasterBlock
import numpy as np
import time
import pandas as pd
from scipy import stats
from collections import OrderedDict
import copy
import pickle

class MultiPath(MasterBlock):
	"""
Children class of MasterBlock. Use it for traction-torsion testing.
	"""
	def __init__(self,path=None,send_freq=400,labels=['t(s)','dep(mm)','angle(deg)'],surface=None,repeat=False):
		"""
		
WIP

SignalGenerator(path=None,send_freq=800,repeat=False,labels=['t(s)','signal'])

Calculate a signal, based on the time (from t0). There is several configurations,
see the examples section for more details.

Parameters
----------
path : list of dict
	Each dict must contain parameters for one step. See Examples section below.
	Available parameters are :
	* waveform : {'sinus','square','triangle','limit','hold'}
		Shape of your signal, for every step.
	* freq : int or float
		Frequency of your signal.
	* time : int or float or None
		Time before change of step, for every step. If None, means infinite.
	* cycles : int or float or None (default)
		Number of cycles before change of step, for every step. If None, means infinite.
	* amplitude : int or float
		Amplitude of your signal.
	* offset: int or float
		Offset of your signal.
	* phase: int or float
		Phase of your signal (in radians). If waveform='limit', phase will be 
		the direction of the signal (up or down).
	* lower_limit : [int or float,sting]
		Only for 'limit' mode. Define the lower limit as a value of the
		labeled signal : [value,'label']
	* upper_limit : [int or float,sting]
		Only for 'limit' mode. Define the upper limit as a value of the 
		labeled signal : [value,'label']
send_freq : int or float , default = 800
	Loop frequency. Use this parameter to avoid over-use of processor and avoid
	filling the link too fast.
repeat : Boolean, default=False
	Set True is you want to repeat your sequence forever.
labels : list of strings, default =['t(s)','signal']
	Allows you to set the labels of output data.

Returns:
--------
Panda Dataframe with time and signal. If waveform='limit', signal can be -1/0/1.

Examples:
---------
SignalGenerator(path=[{"waveform":"hold","time":3},
					{"waveform":"sinus","time":10,"phase":0,"amplitude":2,"offset":0.5,"freq":2.5},
					{"waveform":"triangle","time":10,"phase":np.pi,"amplitude":2,"offset":0.5,"freq":2.5},
					{"waveform":"square","time":10,"phase":0,"amplitude":2,"offset":0.5,"freq":2.5}
					{"waveform":"limit","cycles":3,"phase":0,"lower_limit":[-3,"signal"],"upper_limit":[2,"signal"]}],
					send_freq=400,repeat=True,labels=['t(s)','signal'])
In this example we displayed every possibility or waveform.
Every dict contains informations for one step.
The requiered informations depend on the type of waveform you need.

		"""
		print "MultiPath!"
		self.path=path # list of list or arrays
		self.nb_step=len(path)
		self.send_freq=send_freq
		self.repeat=repeat
		self.labels=labels
		self.step=0
		self.surface=110.74*10**(-6)
		self.offset=5*10**(-6)
		self.R_eps=0.0001 # in (0.00005)
		self.D_eps=0.0005 # in  (0.00055)
		self.normal_speed=6.6*10**(-4) #in /s
		self.detection_speed=6.6*10**(-5) # in /s
		self.speed=self.normal_speed
		self.plastic_offset=2*10**(-5)
		self.last_t_goto=0
		self.rmoy=(25+22)*10**(-3)/2
		self.I=np.pi*((25*10**-3)**4-(22*10**-3)**4)/32
		self.plastic_def=0
		self.status=-1
		#self.E=190*10**9
		self.G=69*10**9
		self._relative_total_def=0
		self.E=165546471680.81555
		#self.G=69663620164.045624
		
	def send(self,traction,torsion):
		#while time.time()-self.last_t<1./self.send_freq:
			#time.sleep(1./(100*self.send_freq))
		self.last_t=time.time()					
		#Array=pd.DataFrame([[self.last_t-self.t0,traction,torsion]],columns=['t(s)','def(%)','dist(deg)']) # not very good to force labels
		Array=OrderedDict(zip(['t(s)','def(%)','dist(deg)','def_plast(%)','E(Pa)','G(Pa)','status','relative_eps_tot'],[self.last_t-self.t0,traction,torsion,self.plastic_def,self.E,self.G,self.status,self._relative_total_def]))
		#print "array : ",Array
		try:
			for output in self.outputs:
				output.send(Array)
		except:
			pass
	
	def return_elastic(self):
		# eval the closest vector and start detecting the border
		self.initial_total_def=self.total_def
		self.initial_position=self.position
		while self.total_def>(self.initial_total_def-0.001): # go back from 0.1%
			self.goto([0,0],mode="towards")
			self.get_position()
			
	def detection(self):
		self.detection_step=0
		self.first_step_of_detection=True
		self.speed=self.detection_speed
		self.plastic_def=0
		self.denoiser=0
		self.FIFO=[]
		while self.detection_step<16: # while we doesn't have 16 points for the plasticity surface
			#print "11"
			self.get_position()
			#self.initial_position=self.position 
			#print self.position, self.initial_position
			if self.first_step_of_detection:
				self.status=0
				tilt=False
				print "detecting central position and evaluating vectors..."
				self.central_position=self.position
				self.central_effort=self.effort
				try:
					first_vector=np.subtract(self.initial_position,self.position)/np.linalg.norm(np.subtract(self.initial_position,self.position))
					ratio=abs(max(first_vector[0],first_vector[1])/min(first_vector[0],first_vector[1]))
					if ratio>5 or ratio<0.2: # if first vector is too close to axis (approx 10-15deg), tilt it.
						tilt=True
				except AttributeError: # if initial_position is not defined, means this is the first detection
					first_vector=[1,0]
					tilt=True
				a0=np.angle(np.complex(first_vector[0],first_vector[1]))
				#angles=np.arange(a0,a0+2*np.pi,np.pi/16.) # create 16 vectors equali oriented.
				angles=np.arange(a0,a0+2*np.pi,np.pi/8.) # create 16 vectors equali oriented.
				angles[1::2]+=np.pi #reorganized vectors
				if tilt:
					angles+=np.pi/16.
				self.target_positions=[np.cos(angles)*10,np.sin(angles)*10*np.sqrt(3)]# normalized positions, multiplied by 10 to be unreachable
				self.first_step_of_detection=False
				self.detection_substep=0
			#print first_vector
			#self._relative_total_def=np.sqrt((self.position[0]-self.central_position[0])**2+((self.position[1]-self.central_position[1])**2)/3.)
			if self.detection_substep==0: # if going toward plasticity
				try:
					self.goto([self.target_positions[0][self.detection_step],self.target_positions[1][self.detection_step]],mode="towards") # move a little to detetc the plasticity surface
					#print self.target_positions
					self.get_position()
					self._relative_total_def=np.sqrt((self.position[0]-self.central_position[0])**2+((self.position[1]-self.central_position[1])**2)/3.)
					if self.status>self.detection_step:
						self.FIFO.insert(0,np.sqrt((self.position[0]-self.eps0-(self.effort[0]-self.F0)/self.E)**2+((self.position[1]-self.gam0-(self.effort[1]-self.C0)/self.G)**2)/3.))
						if len(self.FIFO)>10:
							self.FIFO.pop()
						self.plastic_def=np.median(self.FIFO)
					if self._relative_total_def<self.R_eps:
						print "eliminating first points"
						self.status=self.detection_step+0.0
					elif self._relative_total_def<self.R_eps+self.D_eps: # eval E and G
						if self.first_of_branch:
							self.eps0=self.position[0]
							self.F0=self.effort[0]
							self.gam0=self.position[1]
							self.C0=self.effort[1]
							self.eps=[]
							self.F=[]
							self.gam=[]
							self.C=[]
							self.first_of_branch=False
							print "15"
						self.eps.append(self.position[0]-self.eps0)
						self.F.append(self.effort[0]-self.F0)
						self.gam.append(self.position[1]-self.gam0)
						self.C.append(self.effort[1]-self.C0)
						if len(self.eps)>15:
							self.E, intercept, self.r_value_E, p_value, std_err = stats.linregress(self.eps,self.F)
							self.G, intercept, self.r_value_G, p_value, std_err = stats.linregress(self.gam,self.C)
							if self.r_value_E<0.99:
								self.E=165*10**9
							if self.r_value_G<0.99:
								self.G=69*10**9
						self.status=self.detection_step+0.1
						print "evaluating E and G"
					elif self.plastic_def<self.plastic_offset:
						#self.plastic_def=np.sqrt((self.position[0]-self.eps0-(self.effort[0]-self.F0)/self.E)**2+((self.position[1]-self.gam0-(self.effort[1]-self.C0)/self.G)**2)/3.)
						#self.eps=[]
						#self.F=[]
						#self.gam=[]
						#self.C=[]
						self.status=self.detection_step+0.2
						print "detecting plasticity..."
					else: # if plasticity
						self.denoiser+=1
						#self.plastic_def=np.sqrt((self.position[0]-self.eps0-(self.effort[0]-self.F0)/self.E)**2+((self.position[1]-self.gam0-(self.effort[1]-self.C0)/self.G)**2)/3.)
						if self.denoiser>5: # ensure 5 measured points in plasticity to avoid noise
							self.detection_substep=1
							self.first_of_branch=True
							self.status=self.detection_step+0.3
							self.denoiser=0
							self.FIFO=[]
							print "Plasticity detected !"
							#print type([self.E,self.G,self.eps,self.F,self.gam,self.C])
							#outfile=open("/home/corentin/Bureau/data_"+str(self.detection_step), "wb" )
							#pickle.dump([self.E,self.G,self.eps,self.F,self.gam,self.C], outfile)
							#np.save('/home/corentin/Bureau/data_'+str(self.detection_step),np.asarray([self.E,self.G,self.eps,self.F,self.gam,self.C]))
							print "E, G : ", self.E, self.G
							print "coeffs E, G : ", self.r_value_E, self.r_value_G
							#print "eps: ", self.eps
							#print "F :",self.F
							#print "dist :", self.gam
							#print "C :", self.C
				except ZeroDivisionError:
					print "E and/or G are not defined, please check your parameters"
			else: # if detection_substep==1, going back to center
				#self.E=0
				#self.G=0
				print "going back to center"
				#self.status=self.detection_step+0.4
				self.goto(self.central_position,mode="absolute")
				self.status=self.detection_step+0.4
				self.detection_substep=0
				self.detection_step+=1
				self.plastic_def=0
				print "moving to next vector : ", self.detection_step
		self.speed=self.normal_speed # setting back the normal speed
		self.status=-1
		print "plasticity surface detected"

	
	def get_position(self): # get position and eval total stress
		#self.outputs[0].send("trigger signal")
		self.Data=self.inputs[0].recv()
		#print self.Data
		#self.position=[self.Data[self.labels[1]],self.Data[self.labels[3]]]
		#self.effort=[self.Data[self.labels[2]]/self.surface,(self.Data[self.labels[4]]/self.I)*self.rmoy]
		#self.total_def=np.sqrt((self.position[0])**2+((self.position[1])**2)/3.)
		self.position=[self.Data['def(%)'],self.Data['dist(deg)']]
		self.effort=[self.Data['sigma(Pa)'],self.Data['tau(Pa)']]
		self.total_def=self.Data['eps_tot(%)']

		#print self.position, self.effort, self.total_def

	def goto(self,target,mode="towards"): # go to absolute position, use as a substep in main loop
		if mode=="towards":
			#########################print "going to : " ,target
			if time.time()-self.last_t_goto>1:
				self.last_t_goto=time.time()
			if np.linalg.norm(np.subtract(target,self.position))>self.offset:
				self.vector=np.subtract(target,self.position)/np.linalg.norm(np.subtract(target,self.position))
				#self.traction=self.position[0]+self.speed*self.vector[0]
				#self.torsion=self.position[1]+self.speed*self.vector[1]
				t=time.time()
				#print "vector : " , self.vector
				#print "delta t : ", (t-self.last_t_goto)
				#print "speed : ", self.speed
				try :
					#print "1111111111111111111111111111111111111111111"
					self.traction+=self.speed*self.vector[0]*(t-self.last_t_goto)
					self.torsion+=self.speed*self.vector[1]*(t-self.last_t_goto)
				except AttributeError:
					#print "222222222222222222222222222222222222222222222222222"
					self.traction=self.position[0]+self.speed*self.vector[0]*(t-self.last_t_goto)
					self.torsion=self.position[1]+self.speed*self.vector[1]*(t-self.last_t_goto)
				self.last_t_goto=t
				#print "sending towards : ", self.traction, self.torsion
				self.send(self.traction,self.torsion)
		elif mode=="absolute":
			t0=time.time()
			#self.vector=np.subtract(target,self.position)/np.linalg.norm(np.subtract(target,self.position))
			while np.linalg.norm(np.subtract(target,self.position))>self.offset:
				#print "moving"
				self.vector=np.subtract(target,self.position)/np.linalg.norm(np.subtract(target,self.position))
				#print self.vector, self.position, target
				t=time.time()
				#self.traction=self.position[0]+self.speed*self.vector[0]
				#self.torsion=self.position[1]+self.speed*self.vector[1]
				try:
					self.traction+=self.speed*self.vector[0]*(t-t0)
					self.torsion+=self.speed*self.vector[1]*(t-t0)
				except AttributeError:
					self.traction=self.position[0]+self.speed*self.vector[0]*(t-t0)
					self.torsion=self.position[1]+self.speed*self.vector[1]*(t-t0)
				t0=t
				#print "sending : ",self.traction,self.torsion
				#self.traction*=100.
				self.send(self.traction,self.torsion)
				self.get_position()
		
	def main(self):
		self.last_t=self.t0
		self.first_of_branch=True
		for i in range(100):
			self.get_position()
		print "initial_position : ", self.position
		#self.initial_position=self.position
		#print "1"
		#self.goto([0.1-self.position[0],0-self.position[1]],mode="absolute")
		self.detection()
		#print "2"
		#while self.step < self.nb_step:
			#print "3"
			#self.goto(self.path[self.step],mode="absolute")
			#self.return_elastic()
			#print "4"
			#self.detection()
			#self.step+=1
		
		
#######   Write Crappy:
	#def main(self): 
		#self.last_t=self.t0
		#self.first_of_branch=True
		#xc=np.asarray([1,0,0,1])
		#xr=np.asarray([0,0,1,1,0,1])+max(xc)+0.2
		#xa=np.asarray([0,0,1,1,0,1,1])+max(xr)+0.2
		#xp1=np.asarray([0,0,1,1,0,1,1])+max(xa)+0.2
		#xp2=np.asarray([0,0,0,1,1,0,1])+max(xp1)+0.2
		#xy=np.asarray([0,0.5,0,1])+max(xp2)+0.2
		#x=np.concatenate((xc,xr,xa,xp1,xp2,xy))
		#x/=max(x)
		#x-=0.5

		#yc=np.asarray([1,1,0,0])
		#yr=np.asarray([0,1,1,0.5,0.5,0])
		#ya=np.asarray([0,1,1,0.5,0.5,0.5,0])
		#yp1=np.asarray([0,1,1,0.5,0.5,0.5,1])
		#yp2=np.asarray([1,0,0.5,0.5,1,1,1])
		#yy=np.asarray([1,0.5,0,1])
		#y=np.concatenate((yc,yr,ya,yp1,yp2,yy))
		#self.get_position()
		#x1=np.empty(0)
		#y1=np.empty(0)
		#for k in range(len(x)-1):
			#x1=np.concatenate((x1,np.linspace(x[k],x[k+1],20)))
			#y1=np.concatenate((y1,np.linspace(y[k],y[k+1],20)))
		##x1=np.linspace(min(x),max(x),1000)
		##y1=np.interp(x1,x,y)
		##plt.plot(x,y,'+b');plt.plot(x1,y1,'r');plt.xlim(-1,1);plt.ylim(-0.1,1.1);plt.show()
		#for step in range(len(x1)):
			#for l in range(10):
				#self.get_position()
				#time.sleep(0.001)
			##self.get_position()
			#self.send(y1[step]/100.,x1[step])
		#while True:
			#time.sleep(0.01)
			#self.get_position()
			#self.send(y1[-1]/100.,x1[-1])
			
######## for batman
	#def main(self):  # for batman
		#import numpy as np
		#import matplotlib.pyplot as plt
		#from skimage import measure
		#import skimage.io
		#self.last_t=self.t0
		#self.first_of_branch=True
		#img=skimage.io.imread("/home/corentin/Bureau/projets/crappy_TTC/batman_logo_by_satanssidekick-d60qtoz.png")
		#img=img>128
		#contours = measure.find_contours(img[::,::,0], 0.8)
		#contours=np.transpose(contours[0])
		#y1=(contours[0])/max(contours[0])
		#x1=((contours[1])/max(contours[1]))/3
		#x1-=np.mean(x1)
		#y1-=np.mean(y1)
		#time.sleep(1)
		#tor=0
		#tra=0
		#for i in range(50):
			#self.get_position()
		#for i in range(1000):
			#tor+=y1[0]/1000.
			#tra+=x1[1]/1000.
			#self.send(tor/100.,tra)
			#self.get_position()
			#time.sleep(0.02)
		#for k in range(3):
			#for step in range(len(x1)):
				#self.get_position()
				#time.sleep(0.02)
				#self.get_position()
				#self.send(y1[step]/100.,x1[step])
		#while True:
			#time.sleep(0.01)
			#self.get_position()
			#self.send(y1[-1]/100.,x1[-1])
		
		
		
########### trefle:
#theta=np.arange(0,2*np.pi,1*10**-4)
#def_=A*np.sin(2*theta)*np.sin(theta+0.75*np.pi)
#dist=np.sqrt(3)*A*np.sin(2*theta)*np.sin(theta+np.pi/4)
#sub_path=zip(def_,dist)
#for i in range(len(sub_path)):
	#self.get_position()
	#self.goto([sub_path[0],sub_path[1]],mode="absolute")
	