"""UI-independent scaling, ROI summaries and bounded plot detail."""
import numpy as np

def scale_image(image,mode='linear',percentile=100):
    out=np.array(image,dtype=float,copy=True)
    finite=np.isfinite(out)
    if finite.any():
        out[finite]=np.minimum(out[finite],np.percentile(out[finite],percentile))
    if mode=='log1p': out=np.log1p(out)
    elif mode=='sqrt': out=np.sqrt(out)
    elif mode!='linear': raise ValueError('Unknown scale')
    return out

def roi_summary(ds,bounds):
    spectrum=ds.spectrum(bounds)
    x0,x1,y0,y1=bounds
    coverage=ds.coverage[y0:y1,x0:x1]
    return {'bounds_exclusive':list(bounds),'counts':int(spectrum.sum()),
            'acquired_source_pixels':int(coverage.sum()),'covered_bins':int((coverage>0).sum()),
            'total_bins':int(coverage.size)},spectrum

def display_spectrum(axis,counts,low,high,max_points=6000):
    """Peak-preserving display decimation: max count per group, original mass positions.
    For plotting only. Exports and ROI sums always retain every original channel.
    """
    if not np.isfinite([low,high]).all() or low>=high: raise ValueError('Mass range needs low < high')
    start=int(np.searchsorted(axis,low)); stop=int(np.searchsorted(axis,high,side='right'))
    if stop-start<=max_points: return axis[start:stop],counts[start:stop]
    edges=np.linspace(start,stop,max_points+1,dtype=int)
    indices=np.array([a+np.argmax(counts[a:b]) for a,b in zip(edges[:-1],edges[1:])])
    return axis[indices],counts[indices]

def image_level(ds,image,level=1):
    """Count-summed display pyramid; never used for analytical ROI extraction."""
    from .binning import spatial_edges
    if level==1: return image,ds.x_edges,ds.y_edges
    ye,xe=spatial_edges(image.shape,max(1,max(image.shape)//level))
    out=np.add.reduceat(np.add.reduceat(np.nan_to_num(image),ye[:-1],axis=0),xe[:-1],axis=1)
    valid=np.add.reduceat(np.add.reduceat(np.isfinite(image).astype(int),ye[:-1],axis=0),xe[:-1],axis=1)>0
    out[~valid]=np.nan
    return out,ds.x_edges[xe],ds.y_edges[ye]
