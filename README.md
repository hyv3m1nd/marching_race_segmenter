# marching_race_segmenter  

Many medical imaging segmentation techniques depend on masking (identifying areas of interest) and color thresholding. However, many medical images are not standardized even within one institution. This is especially common in MRI scans, where some organs can change colors drastically from region to region. While advanced AI based techniques exist, at the time this project was developed (in 2021), I was unaware of an affordable platform that could handle complex pathological cases well while also adhering to my workplace's patient privacy and data sharing rules. Therefore, a complex manual workflow involving multiple sectional thresholds was often needed.  
  
I realized that what I really needed was a structure outline identifier. After a failed attempt to calculate them through changes in neighboring voxel values, I came up with marching race:  
Assuming voxels change colors most drastically at structural borders, I start with a medical image where a small part of each anatomical structure is given a different label. An algorithm then sorts each unlabeled voxel by their color differences from their neighboring labelled voxel. The one with the smallest color difference is labeled, and the label "marches forward". Once two labels collide, they stop marching. The hypothesis is that structural borders are where most marches slow to a crawl and allow opposing marches to catch up.  
  
## The result  
Apart from structures involving composite structures (such as the bowel), this algorithm was fairly accurate when tested on up to 20 structures.  
  
## Algorithmic highlight  
At first, each unlabeled voxel was added to a marching queue by comparing its marching priority (the inverse of color difference) with all other voxels in the queue. The complexity was O(n^2). A high definition torso CT scan with around 31 million voxels tool nearly an entire day on my PC.
When a sorted list was used, the complexity got reduced to O(n log n), and the same CT scan could be processed in 10-30 minutes.

## Potential optimization  
When a step is taken, only calculate the new priorities in the voxels surrounding the newly labeled voxel. I would expect this optimization to cut down the runtime further to around 2 minutes.  

## Note
I later learned that this algorithm works in a similar way to 3D Slicer's flood filling method.  

Code written in 2021
