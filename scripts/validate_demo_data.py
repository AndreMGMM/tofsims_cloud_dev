"""Validate all packaged variants, optionally against the read-only source."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.data_loader import SparseDataset,ROOT

def validate(source=None,qms=None):
    info=json.loads((ROOT/'data/dataset_info.json').read_text())
    rows=[]
    for variant in info['variants']:
        path=ROOT/'data'/variant['file']
        ds=SparseDataset(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==variant['sha256']
        assert list(ds.shape)==variant['spatial_shape']
        assert ds.matrix.shape[1]==info['mass_channels']
        assert int(ds.spectrum().sum())==info['total_counts']
        assert int(ds.coverage.sum())==info['source_stored_pixels']
        assert ds.x_edges[0]==0 and ds.y_edges[0]==0
        assert [int(ds.y_edges[-1]),int(ds.x_edges[-1])]==info['source_spatial_shape']
        assert ds.metadata['calibration']==info['calibration']
        if info['calibration'].get('coefficients') is not None:
            np.testing.assert_array_equal(ds.coefficients,info['calibration']['coefficients'])
        with np.load(path,allow_pickle=False) as z:
            np.testing.assert_array_equal(ds.spectrum(),z['source_summed_spectrum'])
            if 'source_tissue_mask' in z:
                mask=z['source_tissue_mask']>0
                ye,xe=ds.y_edges,ds.x_edges
                expected=np.add.reduceat(np.add.reduceat(mask.astype(int),ye[:-1],axis=0),xe[:-1],axis=1)
                np.testing.assert_allclose(z['tissue_fraction']*np.diff(ye)[:,None]*np.diff(xe)[None,:],expected)
        if source:
            source=Path(source)
            assert hashlib.sha256(source.read_bytes()).hexdigest()==info['source_sha256']
            axis_path=Path(qms) if qms else source.with_name(source.stem+'_qms.npy')
            np.testing.assert_array_equal(ds.mz_raw,np.load(axis_path,allow_pickle=False))
            with np.load(source,allow_pickle=False) as z:
                original=sparse.csr_matrix((z['values'],z['indices'],z['indptr']),shape=(len(z['pixel_x']),len(ds.mz_raw)))
                np.testing.assert_array_equal(ds.spectrum(),np.asarray(original.sum(axis=0)).ravel())
                expected=np.zeros(ds.shape,dtype=np.uint64)
                by=np.searchsorted(ds.y_edges,z['pixel_y'],side='right')-1
                bx=np.searchsorted(ds.x_edges,z['pixel_x'],side='right')-1
                np.add.at(expected,(by,bx),np.asarray(original.sum(axis=1)).ravel())
                np.testing.assert_array_equal(expected,np.nan_to_num(ds.ion_image()).astype(np.uint64))
        rows.append({'file':path.name,'shape':ds.shape,'mass_channels':len(ds.mz_raw),'total_counts':int(ds.spectrum().sum()),'passed':True})
        print(rows[-1])
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source');p.add_argument('--qms');p.add_argument('--report')
    args=p.parse_args();result=validate(args.source,args.qms)
    if args.report:
        output=Path(args.report).resolve()
        if not output.is_relative_to(ROOT): raise ValueError('Report must stay in package')
        output.write_text(json.dumps({'checks':result,'compared_with_original':bool(args.source)},indent=2))
