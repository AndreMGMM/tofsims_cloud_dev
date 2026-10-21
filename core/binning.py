"""Count-preserving sparse spatial aggregation without spectral interpolation."""
import numpy as np
from scipy import sparse

def spatial_edges(shape,target):
    if target < 1: raise ValueError('Target must be positive')
    scale=min(1.0,target/max(shape))
    out=tuple(max(1,round(d*scale)) for d in shape)
    # Exact integer partitions include every edge pixel; variable widths are explicit.
    return tuple(np.arange(n+1,dtype=np.int64)*old//n for old,n in zip(shape,out))

def bin_counts(matrix,x,y,shape,target):
    if matrix.dtype.kind not in 'ui' or (matrix.data<0).any():
        raise ValueError('Only integer counts supported; derived/normalized inputs require an explicit aggregation rule')
    ye,xe=spatial_edges(shape,target)
    ny,nx=len(ye)-1,len(xe)-1
    bx=np.searchsorted(xe,x,side='right')-1
    by=np.searchsorted(ye,y,side='right')-1
    bins=by*nx+bx
    grouping=sparse.csr_matrix((np.ones(len(x),dtype=np.uint64),(bins,np.arange(len(x)))),shape=(ny*nx,len(x)))
    out=grouping @ matrix.astype(np.uint64,copy=False)
    out.sum_duplicates();out.sort_indices();out.eliminate_zeros()
    coverage=np.bincount(bins,minlength=ny*nx).reshape(ny,nx).astype(np.uint32)
    yy,xx=np.indices((ny,nx))
    return out,xx.ravel().astype(np.uint32),yy.ravel().astype(np.uint32),coverage,xe,ye
