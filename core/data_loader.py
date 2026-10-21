"""Sparse counts backend; NPZ materializes compressed members, never a dense cube."""
from __future__ import annotations
import json
from collections import OrderedDict
from pathlib import Path
from typing import Protocol
import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]

class DatasetBackend(Protocol):
    shape: tuple[int, int]
    mz_raw: np.ndarray
    def ion_image(self, low: float | None = None, high: float | None = None,
                  calibrated: bool = False) -> np.ndarray: ...
    def spectrum(self, bounds: tuple[int, int, int, int] | None = None) -> np.ndarray: ...

class SparseDataset:
    """Rows are stored pixels, columns are original mass channels. Missing != zero."""
    def __init__(self, path: str | Path):
        path = Path(path)
        if not path.is_absolute():
            path = ROOT / path
        with np.load(path, allow_pickle=False) as z:
            required = {'indptr','indices','values','shape','pixel_x','pixel_y','mz_raw',
                        'metadata_json','coverage','x_edges','y_edges'}
            if not required <= set(z.files):
                raise ValueError('Unsupported NPZ schema. Use scripts/generate_demo_data.py to convert a source cache with its QMS axis.')
            self.shape = tuple(int(v) for v in z['shape'])
            if len(self.shape) != 2 or min(self.shape) <= 0:
                raise ValueError('Invalid image shape')
            self.mz_raw = z['mz_raw']
            self.x, self.y = z['pixel_x'], z['pixel_y']
            self.metadata = json.loads(str(z['metadata_json']))
            self.assignments = json.loads(str(z['assignments_json'])) if 'assignments_json' in z else []
            self.coefficients = z['calibration_coefficients'] if 'calibration_coefficients' in z else np.array([])
            self.coverage = z['coverage']
            self.x_edges, self.y_edges = z['x_edges'], z['y_edges']
            ip, ix, v = z['indptr'], z['indices'], z['values']
        if self.mz_raw.ndim != 1 or not np.isfinite(self.mz_raw).all() or not np.all(np.diff(self.mz_raw) > 0):
            raise ValueError('Mass axis must be finite and strictly increasing')
        n = len(self.x)
        if self.y.shape != self.x.shape or self.x.ndim != 1 or len(ip) != n+1:
            raise ValueError('Pixel/CSR dimensions disagree')
        if ip[0] != 0 or ip[-1] != len(v) or len(ix) != len(v) or np.any(ip[1:] < ip[:-1]):
            raise ValueError('Invalid CSR pointers')
        if len(ix) and (ix.min() < 0 or ix.max() >= len(self.mz_raw)):
            raise ValueError('Mass index outside axis')
        if n and (self.x.min()<0 or self.y.min()<0 or self.x.max()>=self.shape[1] or self.y.max()>=self.shape[0]):
            raise ValueError('Pixel outside image')
        if len(np.unique(self.y.astype(np.int64)*self.shape[1]+self.x)) != n:
            raise ValueError('Duplicate pixel coordinates')
        if self.coverage.shape != self.shape or np.any(self.coverage < 0):
            raise ValueError('Invalid acquisition coverage')
        if len(self.x_edges)!=self.shape[1]+1 or len(self.y_edges)!=self.shape[0]+1 or np.any(np.diff(self.x_edges)<=0) or np.any(np.diff(self.y_edges)<=0):
            raise ValueError('Invalid spatial bin edges')
        if v.dtype.kind not in 'ui' or np.any(v < 0):
            raise ValueError('This backend accepts nonnegative integer counts only')
        self.matrix = sparse.csr_matrix((v,ix,ip),shape=(n,len(self.mz_raw)))
        self.matrix.check_format(full_check=True)
        self._images = OrderedDict()
        self._spectrum = None
        for a in (self.mz_raw,self.x,self.y,self.coverage,self.x_edges,self.y_edges,self.coefficients,
                  self.matrix.data,self.matrix.indices,self.matrix.indptr):
            a.flags.writeable = False

    def mass_axis(self, calibrated=False):
        if calibrated:
            if not len(self.coefficients):
                raise ValueError('No saved calibration coefficients')
            axis = np.polyval(self.coefficients,self.mz_raw.astype(np.float64))
            if not np.all(np.diff(axis)>0):
                raise ValueError('Saved calibration is not monotonic')
            return axis
        return self.mz_raw

    def ion_image(self, low=None, high=None, calibrated=False):
        key=(low,high,calibrated)
        if key not in self._images:
            if low is None and high is None:
                values=np.asarray(self.matrix.sum(axis=1)).ravel()
            else:
                if low is None or high is None or not np.isfinite([low,high]).all() or low>high:
                    raise ValueError('Specify finite mass bounds, low <= high')
                axis=self.mass_axis(calibrated)
                a,b=np.searchsorted(axis,[low,high],side='left')
                b=int(np.searchsorted(axis,high,side='right'))
                values=np.asarray(self.matrix[:,int(a):b].sum(axis=1)).ravel()
            image=np.full(self.shape,np.nan)
            image[self.y,self.x]=values
            image[self.coverage==0]=np.nan
            image.flags.writeable=False
            self._images[key]=image
            if len(self._images)>8: self._images.popitem(last=False)
        self._images.move_to_end(key)
        return self._images[key]

    def spectrum(self,bounds=None):
        if bounds is None:
            if self._spectrum is None:
                self._spectrum=np.asarray(self.matrix.sum(axis=0)).ravel()
                self._spectrum.flags.writeable=False
            return self._spectrum
        x0,x1,y0,y1=bounds
        if not (0<=x0<x1<=self.shape[1] and 0<=y0<y1<=self.shape[0]):
            raise ValueError('ROI must be within image; end bounds are exclusive')
        rows=(self.x>=x0)&(self.x<x1)&(self.y>=y0)&(self.y<y1)
        return np.asarray(self.matrix[rows].sum(axis=0)).ravel()

    def clear_cache(self):
        self._images.clear()
        self._spectrum=None
