
import os, time, sys
import numpy as np
import scipy.misc as sm
import Image
from pyKinectTools.utils.RealtimeReader import *
import cPickle as pickle

from multiprocessing import Pool, Process, Queue

# DIR = '/Users/colin/Data/icu_test/'
# DIR = '/home/clea/Data/tmp/'
# DIR = '/home/clea/Data/ICU_Nov2012/'
DIR = '/media/Data/icu_test2/'
# DIR = '/media/Data/CV_class/'



def save_frame(depthName=None, depth=None, colorName=None, color=None, userName=None, users=None, mask=None):

	''' Depth '''
	if depthName is not None:
		im = Image.fromarray(depth.astype(np.int32), 'I')
		im = im.resize([320,240])
		im.save(depthName)
		
	'''Mask'''
	if mask is not None and depthName is not None:
			mask = sm.imresize(mask, [240,320], 'nearest')
			sm.imsave(depthName[:-4]+"_mask.jpg", mask)

	'''Color'''
	if colorName is not None:
		color = sm.imresize(color, [240,320,3], 'nearest')
		sm.imsave(colorName, color)

	'''User'''
	if userName is not None:
		usersOut = {}
		for k in users.keys():
				usersOut[k] = users[k].toDict()

		with open(userName, 'wb') as outfile:
				pickle.dump(usersOut, outfile, protocol=pickle.HIGHEST_PROTOCOL)




def main(deviceID=1, dir_=DIR, getSkel=False, frameDifferencePercent=5, anonomize=False, viz=False,  imgStoreCount=10):

		'''------------ Setup Kinect ------------'''
		''' Physical Kinect '''
		depthDevice = RealTimeDevice(device=deviceID, getDepth=True, getColor=True, getSkel=getSkel)
		depthDevice.start()

		maxFramerate = 30
		minFramerate = 1.0/3.0
		motionLagTime = 3
		recentMotionTime = time.clock()

		''' ------------- Main -------------- '''

		''' Setup time-based stuff '''
		prevTime = 0
		prevFrame = 0
		prevFrameTime = 0
		currentFrame = 0;
		ms = time.clock()
		diff = 0

		prevSec = 0;
		secondCount = 0
		prevSecondCountMax = 0

		''' init mask if skeleten and anonomize are on '''
		# if not getSkel:
			# anonomize = False
		# if anonomize:
				# mask = np.ones([480,640])

		''' Ensure base folder is there '''
		if not os.path.isdir(dir_):
				os.mkdir(dir_)        

		depthOld = []
		colorOld = []
		backgroundModel = None

		if viz:
			import cv2
			from pyKinectTools.utils.DepthUtils import world2depth
			cv2.namedWindow("image")        



		while 1:
				# try:
				if 1:

						depthDevice.update()
						colorRaw = depthDevice.colorIm
						depthRaw8 = depthDevice.depthIm
						users = depthDevice.users
						skel = None


						if len(depthOld) == imgStoreCount:
								depthOld.pop(0)        

						''' If framerate is too fast then skip '''
						''' Keep this after update to ensure fast enough kinect refresh '''
						if (time.clock() - float(ms))*1000 < 1000.0/maxFramerate:
								continue                

						if viz and 0:
								for i in depthDevice.user.users:
										tmpPx = depthDevice.user.get_user_pixels(i)

										if depthDevice.skel_cap.is_tracking(i):
												brightness = 50
										else:
												brightness = 150
										depthRaw8 = depthRaw8*(1-np.array(tmpPx).reshape([480,640]))
										depthRaw8 += brightness*(np.array(tmpPx).reshape([480,640]))

						d = None
						d = np.array(depthRaw8)

						d /= (np.nanmin([d.max(), 2**16])/256.0)
						d = d.astype(np.uint8)

						''' Get new time info '''
						currentFrame += 1
						time_ = time.localtime()
						day = str(time_.tm_yday)
						hour = str(time_.tm_hour)
						minute = str(time_.tm_min)
						second = str(time_.tm_sec)
						ms = str(time.clock())
						ms_str = str(ms)[str(ms).find(".")+1:]


						''' Look at how much of the image has changed '''
						if depthOld != []:
								diff = np.sum(np.logical_and((depthRaw8 - depthOld[0]) > 200, (depthRaw8 - depthOld[0]) < 20000)) / 307200.0 * 100

								''' We want to watch all video for at least 5 seconds after we seen motion '''
								''' This prevents problems where there is small motion that doesn't trigger the motion detector '''
								if diff > frameDifferencePercent:
										recentMotionTime = time.clock()

						depthOld.append(depthRaw8)                                

						if anonomize:
							'''Background model'''
							if backgroundModel is None:
								bgSubtraction = AdaptiveMixtureOfGaussians(depthRaw8, maxGaussians=3, learningRate=0.2, decayRate=0.9, variance=100**2)
								backgroundModel = bgSubtraction.getModel()
								continue
							else:
								bgSubtraction.update(depthRaw8)

							backgroundModel = bgSubtraction.getModel()
							cv2.imshow("BG Model", backgroundModel/backgroundModel.max())
							foregroundMask = bgSubtraction.getForeground(thresh=100)
							''' Find people '''
							foregroundMask, _, _ = extractPeople(depthRaw8, foregroundMask, minPersonPixThresh=5000, gradientFilter=True, gradThresh=15)


						''' Write to file if there has been substantial change. '''
						# if 1:
						if diff > frameDifferencePercent or time.clock()-prevFrameTime > 1/minFramerate or time.clock()-recentMotionTime < motionLagTime:
								if depthRaw8 != []:

										''' Logical time '''
										if second != prevSec:
												prevSecondCountMax = secondCount                                
												secondCount = 0
												prevSec = second
										else:
												secondCount = int(secondCount) + 1

										secondCount = str(secondCount)
										if len(ms_str) == 1:
												ms_str = '0' + ms_str
										if len(secondCount) == 1:
												secondCount = '0' + secondCount


										''' Keep track of framerate '''
										if prevTime != second:
												prevTime = second
												# print currentFrame - prevFrame, " fps. Diff = ", str(diff)[:4] + "%" #" #threads = ", len(processList), 
												print "FPS: "+ str(prevSecondCountMax) + " Diff: " + str(diff)[:4] + "%" #" #threads = ", len(processList), 
												prevFrame = currentFrame


										''' Create a folder if it doesn't exist '''
										depthDir = dir_+'depth/'+day+"/"+hour+"/"+minute+"/device_"+str(deviceID)
										colorDir = dir_+'color/'+day+"/"+hour+"/"+minute+"/device_"+str(deviceID)
										skelDir = dir_+'skel/'+day+"/"+hour+"/"+minute+"/device_"+str(deviceID)

										if not os.path.isdir(depthDir):
												for p in xrange(4, len(depthDir.split("/"))+1):                         
														try:
																os.mkdir("/".join(depthDir.split('/')[0:p])) 
																os.mkdir("/".join(colorDir.split('/')[0:p]))
																os.mkdir("/".join(skelDir.split('/')[0:p]))
														except:
																# print "error making dir"
																pass


										''' Define filenames '''
										depthName = depthDir + "/depth_"+day+"_"+hour+"_"+minute+"_"+second+"_"+secondCount+"_"+ms_str+".png"
										colorName = colorDir + "/color_"+day+"_"+hour+"_"+minute+"_"+second+"_"+secondCount+"_"+ms_str+".jpg"
										usersName = skelDir + "/skel_"+day+"_"+hour+"_"+minute+"_"+second+"_"+secondCount+"_"+ms_str+"_.dat"

										''' Save data '''
										''' Anonomize '''
										if anonomize:
												# mask = np.zeros([480,640])

												# if len(depthDevice.user.users) > 0:
												# 		# print depthDevice.user.users            

												# 		for i in depthDevice.user.users:
												# 				np.array(depthDevice.user.get_user_pixels(i)).reshape([480,640])

												# 		mask = np.array(depthDevice.user.get_user_pixels(i)).reshape([480,640])

												save_frame(depthName, depthRaw8, colorName, colorRaw, usersName, users, mask=foregroundMask)
												# save_frame(depthName, depthRaw8, colorName, colorRaw, usersName, users, mask=mask)
										else:
												save_frame(depthName, depthRaw8, colorName, colorRaw, usersName, users)
												

										prevFrameTime = time.clock()



								''' Display skeletons '''
								if 0 and viz:
										# print "Users: ", len(users)
										for u_key in users.keys():
												u = users[u_key]
												pt = world2depth(u.com)
												w = 10
												d[pt[0]-w:pt[0]+w, pt[1]-w:pt[1]+w] = 255
												w = 3
												if u.tracked:
														print "Joints: ", len(u.jointPositions)
														for j in u.jointPositions.keys():
																pt = world2depth(u.jointPositions[j])
																d[pt[0]-w:pt[0]+w, pt[1]-w:pt[1]+w] = 200                                                        


								if viz:
										if 1:
												cv2.imshow("imageD", d)
										if 0:
												# cv2.imshow("imageM", mask/float(mask.max()))
												cv2.imshow("image", colorRaw + (255-colorRaw)*(foregroundMask>0)[:,:,np.newaxis] + 50*(((foregroundMask)[:,:,np.newaxis])))
										if 1:
												cv2.imshow("imageC", colorRaw)
												# cv2.imshow("image", colorRaw + (255-colorRaw)*(foregroundMask>0)[:,:,np.newaxis] + 50*(((foregroundMask)[:,:,np.newaxis])))

										r = cv2.waitKey(10)
										if r >= 0:
												break



if __name__ == "__main__":
		if len(sys.argv) > 1:

				''' Viz? '''
				if len(sys.argv) > 2:
						viz = sys.argv[2]
				else:
						viz = 0

				''' Get frame difference percent '''
				if len(sys.argv) > 3:
						frameDiffPercent = sys.argv[2]
				else:
						frameDiffPercent = -1

				if frameDiffPercent < 0:
						main(deviceID=int(sys.argv[1]), viz=int(viz))
				else:
						main(deviceID=int(sys.argv[1]), viz=int(viz), frameDifferencePercent = 6)   

		else:
				main(1)




''' Multiprocessing '''

## Multiprocessing
# pool = Pool(processes = 1)
# # queue = SimpleQueue()
# processList = []
# processCount = 2



# Update process thread counts
# removeProcesses = []
# for i in xrange(len(processList)-1, -1, -1):
# 		if not processList[i].is_alive():
# 				removeProcesses.append(i)
# for i in removeProcesses:
# 		processList.pop(i)


''' Have it compress/save on another processor '''
# p = Process(target=save_frame, args=(depthName, depthRaw8, colorName, colorRaw, usersName, users))
# p.start()
# processList.append(p)
# print depthName, 1, depthRaw8.dtype

# queue.put((target=save_frame, args=(depthName, depthRaw8, colorName, colorRaw, usersName, users))
# print "Size: ", queue.qsize()
# pool.apply_async(save_frame, args=(depthName=depthName, depth=depthRaw8, colorName=colorName, color=colorRaw, usersName=usersName, users=users))
# pool.apply_async(save_frame, args=(depthName, depthRaw8, colorName, colorRaw, usersName, users))
# pool.apply_async(save_frame(depthName, depthRaw8, colorName, colorRaw, usersName, users))
# pool.join()

# if len(processList) < processCount:
#         p.start()
# else:
#         processList.append(p)

