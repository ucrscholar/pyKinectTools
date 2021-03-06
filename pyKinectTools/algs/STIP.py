import numpy as np
import scipy.misc
import os, sys
import scipy.ndimage as nd
from sklearn import neighbors


## Gabor filter
def generateGabors(angles, size=[20,20], rho=1):
	# angles in degrees
	if type(angles) != list:
		angles = [angles]
	width = size[0]
	height = size[1]

	xsbase = np.array(range(width)).T
	xs = np.array(xsbase, dtype=float)
	for i in range(height-1):
		xs = np.vstack([xs, xsbase])
	xs -= 1.0*width/2
	xs /= width

	ysbase = np.array(range(height)).T
	ys = np.array(ysbase, dtype=float)
	for i in range(width-1):
		ys = np.vstack([ys, ysbase])
	ys = ys.T
	ys -= 1.0*height/2
	ys /= height

	ux = 1.0/(2*rho)
	uy = 1.0/(2*rho)

	# Gaussian envelope
	gauss = np.exp(-0.5*(xs**2/rho**2 + ys**2/rho**2))
	gauss -= gauss.min() 
	gauss / gauss.max()

	if len(angles) > 1:
		gabors = np.empty([size[0], size[1], len(angles)])
	else:
		gabors = np.empty([size[0], size[1]])

	for a in range(len(angles)):
		theta = (angles[a])*np.pi/180
		s = np.cos(2*np.pi*(ux*(np.cos(theta)*xs+np.sin(theta)*ys) +uy*(np.sin(theta)*ys+np.cos(theta)*xs)))
		if len(angles) > 1:
			gabors[:,:,a] = s*gauss
		else:
			gabors[:,:] = s*gauss

	return gabors

def CuboidDetector(sigma=1.5, tau=4):

	delX = int(2*np.ceil(3*sigma)+1)
	delY = delX
	delT = int(2*np.ceil(3*tau)+1)

	xs = np.arange(delX, dtype=np.float)[:,np.newaxis].T.repeat(delY, 0)
	xs -= 1.0*delX/2
	xs /= delX

	ys = np.arange(delY, dtype=np.float)[:,np.newaxis].repeat(delX).reshape([delX, delY])
	ys -= 1.0*delY/2
	ys /= delY

	# Gaussian envelope
	gauss = np.exp(-0.5*(xs**2/sigma**2 + ys**2/sigma**2))
	gauss -= gauss.min() 
	gauss / gauss.max()

	omega = 4./tau
	t = np.ones(delT)
	h_ev = -np.cos(2*np.pi*omega)*np.exp(-t**2 / tau**2)
	h_od = -np.sin(2*np.pi*t*omega)*np.exp(-t**2 / tau**2)

	return gauss, h_ev, h_od



def adaptiveNonMaximalSuppression(pts, vals, radius=1):

	tree = neighbors.NearestNeighbors()
	tree.fit(pts)
	nn = tree.radius_neighbors(pts, radius, return_distance=False)

 	outputPts = []
 	for i in range(len(pts)):
 		
 		if vals[i] >= vals[nn[i]].max():
 			outputPts.append(pts[i])
 			# print vals[i],vals[nn[i]].max(), nn[i], i

 	outputPts = np.array(outputPts)
 	return outputPts





