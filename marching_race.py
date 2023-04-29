import math
import os
import directories
import nrrd
import numpy as np
from datetime import datetime
from tkinter import Tk, filedialog
from sortedcontainers import SortedList

basedir = "C:/Users/Ben/Documents/single lesion in pre-TACE/marching race test"
os.chdir(basedir)

targetscan=''

max_energy = 400. #once a march has exhausted its energy, it no longer expands
expand_to_full = False #if True, max_energy = infinite
dist_energy_multiplier = 0. #now much energy does it take to march 1mm?
slope_energy_multiplier = 1. #how much energy does it take to march one hounsfield unit?
blur = 5 #number of times box blur is applied to the original nrrd before the race commences
use_labelmap = True #converts [targetscan]-label.nrrd to queue entries; if False, define your own queue below

floodfill_directions = {
        'x': True, 
        'y': True, 
        'z': True, 
        'xy': False,
        'xz': False,
        'yz': False,
        'xyz': False
        }

data=[[[]]]
header=''
voxel_size = (1.,1.,1.)
queue = SortedList(key=lambda i: -i[4]) #structure: (x,y,z,group,energy)
new_nrrd=[[[]]]

directions = np.zeros((27,3),dtype='int')
neighbors_coords = np.zeros((27,3),dtype='int')
neighbors_vals = np.zeros(27,dtype='int')

voxels_processed = 0
report = True # prints the progress
report_headers = False #prints the headers of each nrrd it reads
report_progress = False #prints the sizes of the queue and processed voxels
report_progress_details = True # prints the specific label assigned to each voxel

def getfile():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    return file_path

def getfolder():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    open_file = filedialog.askdirectory()
    return open_file

def setparameters(directory='', filename=''):
    global basedir, targetscan, max_energy
    if directory:
        basedir = directory
    if filename:
        targetscan = filename

def set_voxel_size(header):
    global voxel_size
    voxel_size = (header.get('space directions')[0][0], header.get('space directions')[1][1], header.get('space directions')[2][2])
    if report:
        print(f"voxel size: {voxel_size}")

def in_data(x,y,z):
    global data
    x_in_range = x>=0 and x<len(data)
    y_in_range = y>=0 and y<len(data[0])
    z_in_range = z>=0 and z<len(data[0][0])
    return x_in_range and y_in_range and z_in_range

def relevant_directions(x,y,z):
    global directions
    directions[0][0] = 0
    if floodfill_directions.get('x'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x-1,y,z]
        directions[curr_pos+1] = [x+1,y,z]
        directions[0][0] = directions[0][0]+2
    if floodfill_directions.get('y'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x,y-1,z]
        directions[curr_pos+1] = [x,y+1,z]
        directions[0][0] = directions[0][0]+2
    if floodfill_directions.get('z'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x,y,z-1]
        directions[curr_pos+1] = [x,y,z+1]
        directions[0][0] = directions[0][0]+2
    if floodfill_directions.get('xy'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x-1,y-1,z]
        directions[curr_pos+1] = [x-1,y+1,z]
        directions[curr_pos+2] = [x+1,y-1,z]
        directions[curr_pos+3] = [x+1,y+1,z]
        directions[0][0] = directions[0][0]+4
    if floodfill_directions.get('xz'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x-1,y,z-1]
        directions[curr_pos+1] = [x-1,y,z+1]
        directions[curr_pos+2] = [x+1,y,z-1]
        directions[curr_pos+3] = [x+1,y,z+1]
        directions[0][0] = directions[0][0]+4
    if floodfill_directions.get('yz'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x,y-1,z-1]
        directions[curr_pos+1] = [x,y-1,z+1]
        directions[curr_pos+2] = [x,y+1,z-1]
        directions[curr_pos+3] = [x,y+1,z+1]
        directions[0][0] = directions[0][0]+4
    if floodfill_directions.get('xyz'):
        curr_pos = directions[0][0]+1
        directions[curr_pos] = [x-1,y-1,z-1]
        directions[curr_pos+1] = [x-1,y-1,z+1]
        directions[curr_pos+2] = [x-1,y+1,z-1]
        directions[curr_pos+3] = [x-1,y+1,z+1]
        directions[curr_pos+4] = [x+1,y-1,z-1]
        directions[curr_pos+5] = [x+1,y-1,z+1]
        directions[curr_pos+6] = [x+1,y+1,z-1]
        directions[curr_pos+7] = [x+1,y+1,z+1]
        directions[0][0] = directions[0][0]+8
    
def neighbor_coords(x,y,z):
    global neighbors_coords
    neighbors_coords[0][0] = 0
    relevant_directions(x,y,z)
    num_attempts = directions[0][0]
    for i in range(1,num_attempts+1):
        if in_data(*directions[i]):
            curr_pos = neighbors_coords[0][0]+1
            neighbors_coords[curr_pos] = directions[i]
            neighbors_coords[0][0] = neighbors_coords[0][0]+1

def neighbor_vals(x,y,z):
    global neighbors_vals
    neighbors_vals[0] = 0
    relevant_directions(x,y,z)
    num_attempts = directions[0][0]
    for i in range(1,num_attempts+1):
        if in_data(*directions[i]):
            curr_pos = neighbors_vals[0]+1
            neighbors_vals[curr_pos] = int(data[directions[i][0]][directions[i][1]][directions[i][2]])
            neighbors_vals[0] = neighbors_vals[0]+1

def dist(x0,y0,z0,x1,y1,z1):
    x_dist = abs(x1-x0)*voxel_size[0]
    y_dist = abs(y1-y0)*voxel_size[1]
    z_dist = abs(z1-z0)*voxel_size[2]
    corners = floodfill_directions.get('xy') or floodfill_directions.get('xz') or floodfill_directions.get('yz') or floodfill_directions.get('xyz')
    if corners:
        return math.sqrt(x_dist**2 + y_dist**2 + z_dist**2)
    else:
        return x_dist + y_dist + z_dist

def slope(x0,y0,z0,x1,y1,z1):
    voxel0 = data[x0][y0][z0]
    voxel1 = data[x1][y1][z1]
    return abs(int(voxel1)-int(voxel0))

def energy_cost(x0,y0,z0,x1,y1,z1):
    dist_cost = 0
    if dist_energy_multiplier: 
        dist_cost = dist_energy_multiplier * dist(*(x0,y0,z0),*(x1,y1,z1))
    slope_cost = slope_energy_multiplier * slope(*(x0,y0,z0),*(x1,y1,z1))
    return dist_cost + slope_cost

"""
def less_energy(comparer, comparee):
    return comparer[4] < comparee[4]

def compare_and_add(race_candidate, queue_start, queue_end):
    global queue
    if not queue:
        queue.append(race_candidate)
        return
    if queue_start > queue_end:
        queue.insert(queue_start, race_candidate)
        return
    compare_position = int((queue_end+queue_start)/2)
    comparee = queue[compare_position]
    push_back = less_energy(race_candidate, comparee)
    if push_back:
        compare_and_add(race_candidate, compare_position+1,queue_end)
    else:
        compare_and_add(race_candidate, queue_start, compare_position-1)

def add_to_queue(race_candidate):
    compare_and_add(race_candidate,0,len(queue)-1)
"""

def grow(x,y,z,group,energy_used=0):
    global new_nrrd, queue, voxels_processed
    if expand_to_full or energy_used<=max_energy:
        new_nrrd[x][y][z]=group
        voxels_processed = voxels_processed+1
        if report_progress:
            print(f"queue size: {len(queue):,}, processed {voxels_processed:,}/{total_voxels:,} voxels")
        if report_progress_details:
            print(f"label at ({x},{y},{z}) is set to {group:,}; energy used: {energy_used}:,")
        neighbor_coords(x,y,z)
        for i in range(1,neighbors_coords[0][0]+1):
            (x1,y1,z1) = (neighbors_coords[i][0],neighbors_coords[i][1],neighbors_coords[i][2])
            if not new_nrrd[x1][y1][z1]:
                new_energy = energy_used+energy_cost(*(x,y,z),*(x1,y1,z1))
                print(f"({x1},{y1},{z1}): {new_energy}")
                race_candidate = (x1,y1,z1,group,new_energy)
                #add_to_queue(race_candidate)
                #print(isinstance(queue, SortedList))
                queue.add(race_candidate)

def queue_from_labelmap_matrix(labelmap_matrix):
    global queue
    for i in range(0,len(labelmap_matrix)):
        for j in range(0,len(labelmap_matrix[0])):
            for k in range(0,len(labelmap_matrix[0][0])):
                if labelmap_matrix[i][j][k]:
                    queue.add((i,j,k,labelmap_matrix[i][j][k],0))

def queue_from_labelmap():
    global queue
    queue = SortedList(key=lambda i: -i[4])
    labelmap_data, labelmap_header = directories.loadnrrd(basedir+'/'+targetscan[0:-5]+'-label.nrrd', report)
    if report_headers:
        print(f"label header: {labelmap_header}")
    queue_from_labelmap_matrix(labelmap_data)

def dimensions(array):
    if isinstance(array, np.int64) or isinstance(array, np.int32) or isinstance(array, np.int16) or isinstance(array, np.uint64) or isinstance(array, np.uint32) or isinstance(array, np.uint16) or isinstance(array, np.float64) or isinstance(array, np.float32) or isinstance(array, np.float16):
        return 0
    curr_dimension = len(array)
    next_dimensions = dimensions(array[0])
    if next_dimensions:
        return (curr_dimension,)+next_dimensions
    else:
        return (curr_dimension,)

def default_array():
    return np.zeros(dimensions(data))

def blur_voxel(x,y,z):
    global neighbors_vals
    voxel0 = data[x][y][z]
    neighbor_vals(x,y,z)
    neighbors_vals[0] = voxel0
    blur_val = sum(neighbors_vals)/len(neighbors_vals)
    return blur_val

def boxblur_once():
    global data
    blurred_data = default_array()
    for i in range(0,len(blurred_data)):
        for j in range(0,len(blurred_data[0])):
            for k in range(0,len(blurred_data[0][0])):
                blurred_data[i][j][k] = blur_voxel(i,j,k)
    data = blurred_data

def apply_blur():
    for i in range(0,blur):
        boxblur_once()            
        if report_progress:
            print(f"blurred {i+1} times")

def runonce(directory='', filename='', name_attachment='_'):
    global data, header, new_nrrd, queue, voxels_processed, total_voxels
    voxels_processed = 0
    setparameters(directory, filename)
    data, header = directories.loadnrrd(basedir+'/'+targetscan, report)
    if report_headers:
        print(f"header: {header}")
    set_voxel_size(header)
    array_dimensions = dimensions(data)
    total_voxels = array_dimensions[0]*array_dimensions[1]*array_dimensions[2]
    if report:
        print(f"dimensions read: {array_dimensions}")
    apply_blur()
    new_nrrd = default_array()
    if report:
        print('Starting at: ', datetime.now())
    if use_labelmap:
        queue_from_labelmap()
    while queue:
        grow(*queue.pop())
    if report:
        print('Finished at: ', datetime.now())
    filename = targetscan[0:-5]
    new_name = filename+name_attachment+'-label.nrrd'
    directories.savenrrd(basedir+'/'+new_name, new_nrrd, header, report)

use_labelmap=True
expand_to_full=False
runonce(filename='5587450_T1C.nrrd', name_attachment=f"_{int(max_energy)}_min_input_from_labelmap")
