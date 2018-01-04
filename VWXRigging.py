from vs import *

class Rig():

	def __init__(self):
		self.obj_handles = []
		self.obj_coords = []
		self.truss_handles = []
		self.hoist_loads = []
		
		self.GetSelectedHandles()
		self.GetRigPoints()
		self.RigObjects()
		
		total = 0
		for i in self.hoist_loads: total += i
		
		Message("Total weight: ", str(total), "lbs. Load per Hoist: ", str(self.hoist_loads))
		
	def getDist(self, p1, p0):
		return Sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)
		
	def getWeight(self, h):
		weight = GetRField(h, "Lighting Device", "Weight")
		if weight.endswith(" lbs"):
			weight = weight[:-4]
		elif weight.endswith("lbs"):
			weight = weight[:-3]
		return float(weight)


		
	def GetSelectedHandles(self):
		# For each object in the active layer, get the object's handle.
		for i in range(NumSObj(ActLayer())):
			current_obj = FSActLayer()
			if GetName(GetRecord(current_obj, 1)) == "Truss Record":
				self.truss_handles.append(current_obj)
			elif GetParametricRecord(current_obj) is not None:
				self.obj_handles.append(current_obj)
			SetDSelect(current_obj)
		
		# Uses voodoo magic to sort the original handles list by coordinates. 
		self.obj_handles = [x for (y, x) in sorted(zip([(GetSymLoc(i)[0] + GetSymLoc(i)[1]) for i in self.obj_handles], self.obj_handles))]
		# Get self.obj_coords afterwards so that they're in the same order as the object handles.
		for i in self.obj_handles:
			self.obj_coords.append(GetSymLoc(i))
			SetSelect(i)
		for i in self.truss_handles:
			SetSelect(i)
			
			
	def GetRigPoints(self):
		# Get the first hoist location
		for i in range(len(self.obj_handles)):
			if GetName(GetParametricRecord(self.obj_handles[i])) == "HoistVW":
				MoveTo(self.obj_coords[i])
				first_hoist = i;
				break
		# Get the last hoist location
		for i in reversed(range(len(self.obj_handles))):
			if GetName(GetParametricRecord(self.obj_handles[i])) == "HoistVW":
				LineTo(self.obj_coords[i])
				last_hoist = i
				break
		rig_line_handle = LNewObj()
		rig_line_rad = Deg2Rad(HAngle(rig_line_handle))
		# Any cantilever longer than 30' would mess up the code, but this would not get past the user.
		new_pt1 = GetSegPt1(rig_line_handle)[0] - (360 * Cos(rig_line_rad)), GetSegPt1(rig_line_handle)[1] - (360 * Sin(rig_line_rad))
		new_pt2 = GetSegPt2(rig_line_handle)[0] + (360 * Cos(rig_line_rad)), GetSegPt2(rig_line_handle)[1] + (360 * Sin(rig_line_rad))
		SetSegPt1(rig_line_handle, new_pt1)
		SetSegPt2(rig_line_handle, new_pt2)
		# We want rig points for every object in the truss except for the first and last hoists because the rig line is drawn from the first hoist to the last.
		for i in [x for x in range(len(self.obj_handles)) if x not in [first_hoist, last_hoist]]:
			MoveTo(self.obj_coords[i])
			LineTo((self.obj_coords[i][0] + 36 * Cos(rig_line_rad + Deg2Rad(90)), self.obj_coords[i][1] + 36 * Sin(rig_line_rad + Deg2Rad(90))))
			new_pt = self.obj_coords[i][0] + 36 * Cos(rig_line_rad + Deg2Rad(270)), self.obj_coords[i][1] + 36 * Sin(rig_line_rad + Deg2Rad(270))
			SetSegPt1(LNewObj(), new_pt)
			# This is where we overide the self.obj_coords of each object to their proper rig points.
			self.obj_coords[i] = LineLineIntersection(GetSegPt1(rig_line_handle), GetSegPt2(rig_line_handle), GetSegPt1(LNewObj()), GetSegPt2(LNewObj()))[2]
			DelObject(LNewObj())
		DelObject(rig_line_handle)
	
	def RigObjects(self):
		x = 10
		hoist_idxs = []
		
		# Get all the hoist positions
		for i in range(len(self.obj_handles)):
			if GetName(GetParametricRecord(self.obj_handles[i])) == "HoistVW":
				hoist_idxs.append(i)
				self.hoist_loads.append(0)
			
		left_load, total_load = 0, 0
		
		for h_num, idx in enumerate(hoist_idxs[:-1]):
			for obj in range(idx+1,hoist_idxs[h_num+1]):
				left_load += self.getDist(self.obj_coords[idx], self.obj_coords[obj]) / self.getDist(self.obj_coords[idx], self.obj_coords[hoist_idxs[h_num+1]]) * (self.getWeight(self.obj_handles[obj]) + x)
				total_load += self.getWeight(self.obj_handles[obj]) + x
			self.hoist_loads[h_num] += round(left_load, 3)
			self.hoist_loads[h_num+1] += round(total_load - left_load, 3)
			left_load, total_load = 0, 0
		
		if hoist_idxs[0] != 0:
			for idx in range(hoist_idxs[0]):
				left_load += self.getDist(self.obj_coords[hoist_idxs[-2]], self.obj_coords[idx]) / self.getDist(self.obj_coords[hoist_idxs[-2]], self.obj_coords[hoist_idxs[-1]]) * (self.getWeight(self.obj_handles[obj]) + x)
				total_load += self.getWeight(self.obj_handles[obj]) + x
			self.hoist_loads[1] += -left_load + total_load
			self.hoist_loads[0] += left_load
		if hoist_idxs[-1] != len(self.obj_handles) - 1:
			for idx in range(hoist_idxs[-1]+1, len(self.obj_handles)):
				left_load += self.getDist(self.obj_coords[hoist_idxs[-2]], self.obj_coords[idx]) / self.getDist(self.obj_coords[hoist_idxs[-2]], self.obj_coords[hoist_idxs[-1]]) * (self.getWeight(self.obj_handles[obj]) + x)
				total_load += self.getWeight(self.obj_handles[obj]) + x
			self.hoist_loads[-2] += round(-left_load + total_load, 3)
			self.hoist_loads[-1] += round(left_load, 3)
		

Rig()


