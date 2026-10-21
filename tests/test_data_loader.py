import json
import numpy as np
import pytest
from scipy import sparse
from core.data_loader import SparseDataset,ROOT
from core.binning import bin_counts,spatial_edges
from core.data_processing import roi_summary,scale_image,display_spectrum,image_level
from gui.components import ion_figure,spectrum_figure

@pytest.fixture(scope='module')
def ds(): return SparseDataset('data/tofsims_demo_256.npz')

def test_packaged_counts_and_mass(ds):
    info=json.loads((ROOT/'data/dataset_info.json').read_text())
    assert ds.shape==(256,205)
    assert ds.matrix.shape==(52480,362573)
    assert int(ds.spectrum().sum())==info['total_counts']
    assert int(ds.coverage.sum())==59392
    with np.load(ROOT/'data/tofsims_demo_512.npz',allow_pickle=False) as native:
        np.testing.assert_array_equal(ds.mz_raw,native['mz_raw'])
        np.testing.assert_array_equal(ds.coefficients,native['calibration_coefficients'])
        assert ds.mz_raw.dtype==native['mz_raw'].dtype
    assert not ds.metadata['calibration']['quality_pass']
    assert len(ds.assignments)>0

def test_tic_and_missing_pixels(ds):
    image=ds.ion_image()
    assert np.isnan(image[ds.coverage==0]).all()
    assert int(np.nansum(image))==int(ds.spectrum().sum())
    assert ds.ion_image() is image
    assert not image.flags.writeable

def test_window_matches_spectrum(ds):
    low,high=78.877957,79.037957
    keep=(ds.mz_raw>=low)&(ds.mz_raw<=high)
    assert int(np.nansum(ds.ion_image(low,high)))==int(ds.spectrum()[keep].sum())
    corrected=ds.mass_axis(True)
    np.testing.assert_array_equal(corrected,np.polyval(ds.coefficients,ds.mz_raw.astype(float)))
    keep=(corrected>=low)&(corrected<=high)
    assert int(np.nansum(ds.ion_image(low,high,True)))==int(ds.spectrum()[keep].sum())

def test_roi_spectrum(ds):
    box=(9,41,12,56);result,spec=roi_summary(ds,box)
    assert result['counts']==int(spec.sum())
    assert result['counts']==int(np.nansum(ds.ion_image()[12:56,9:41]))
    assert result['acquired_source_pixels']==int(ds.coverage[12:56,9:41].sum())
    for bad in [(0,0,0,1),(-1,2,0,2),(0,206,0,2)]:
        with pytest.raises(ValueError): ds.spectrum(bad)

def test_permuted_sparse_pixels_and_edges():
    # Explicit coordinates intentionally disagree with dense row order; an empty row is included.
    x=np.array([4,0,2,1]);y=np.array([2,0,1,2])
    a=sparse.csr_matrix(np.array([[0,7],[3,0],[0,0],[5,11]],dtype=np.uint32))
    b,bx,by,cov,xe,ye=bin_counts(a,x,y,(3,5),3)
    assert cov.shape==(2,3)
    assert xe.tolist()==[0,1,3,5] and ye.tolist()==[0,1,3]
    expected=np.zeros((2,3,2),dtype=np.uint64)
    for row,(cx,cy) in enumerate(zip(x,y)):
        expected[np.searchsorted(ye,cy,side='right')-1,np.searchsorted(xe,cx,side='right')-1]+=a.toarray()[row]
    np.testing.assert_array_equal(b.toarray().reshape(2,3,2),expected)
    assert int(cov.sum())==4
    np.testing.assert_array_equal(b.sum(axis=0),a.sum(axis=0))

def test_uint32_overflow_avoided():
    a=sparse.csr_matrix(np.array([[2**32-1],[2**32-1]],dtype=np.uint32))
    b,*_=bin_counts(a,np.array([0,1]),np.array([0,0]),(1,2),1)
    assert int(b.data[0])==2*(2**32-1)
    assert b.dtype==np.uint64

def test_reject_normalized_input():
    a=sparse.csr_matrix(np.array([[0.5]]))
    with pytest.raises(ValueError): bin_counts(a,np.array([0]),np.array([0]),(1,1),1)

@pytest.mark.parametrize('shape,target',[((5,9),4),((7,3),256),((1,9),2),((320,256),256),((320,256),512)])
def test_partition_all_edge_pixels(shape,target):
    ye,xe=spatial_edges(shape,target)
    assert ye[0]==xe[0]==0 and ye[-1]==shape[0] and xe[-1]==shape[1]
    assert np.all(np.diff(ye)>0) and np.all(np.diff(xe)>0)
    assert len(ye)-1<=shape[0] and len(xe)-1<=shape[1]
    assert max(len(ye)-1,len(xe)-1)<=target

def test_scaling_and_pyramid(ds):
    raw=ds.ion_image();before=raw.copy()
    clipped=scale_image(raw,'log1p',99)
    np.testing.assert_array_equal(raw,before)
    assert np.nanmax(clipped)<np.nanmax(raw)
    view,xe,ye=image_level(ds,raw,4)
    assert int(np.nansum(view))==int(np.nansum(raw))
    assert xe[-1]==256 and ye[-1]==320

def test_spectrum_display_keeps_real_mass_positions():
    mz=np.arange(10000)/10;counts=np.zeros(10000,dtype=int);counts[1234]=999
    x,y=display_spectrum(mz,counts,0,1000,max_points=100)
    assert len(x)==100 and y.max()==999
    assert x[y.argmax()]==mz[1234]
    fine_x,fine_y=display_spectrum(mz,counts,120,125,max_points=100)
    np.testing.assert_array_equal(fine_x,mz[1200:1251])

def test_figures_use_real_edges(ds):
    f=ion_figure(ds,ds.ion_image(),bounds=(1,3,2,7))
    assert len(f.data[0].x)==206 and len(f.data[0].y)==257
    assert f.layout.shapes[0].x0==ds.x_edges[1]
    s=spectrum_figure(ds,ds.spectrum(),60.5,3001)
    assert len(s.data[0].x)<=6000
    json.loads(f.to_json());json.loads(s.to_json())

def test_no_pickle_or_unknown_cube(tmp_path):
    p=tmp_path/'wrong.npz';np.savez_compressed(p,cube=np.ones((2,2,2)))
    with pytest.raises(ValueError,match='Unsupported NPZ schema'): SparseDataset(p)

def test_cache_bounded(ds):
    for mass in range(100,112): ds.ion_image(mass,mass+.1)
    assert len(ds._images)<=8
