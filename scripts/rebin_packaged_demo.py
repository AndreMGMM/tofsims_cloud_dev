"""Regenerate the 256 demo from the included native-resolution 512-cap demo."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.data_loader import ROOT,SparseDataset
from core.binning import bin_counts

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=int,default=256);p.add_argument('--overwrite',action='store_true')
    args=p.parse_args()
    source=ROOT/'data/tofsims_demo_512.npz';ds=SparseDataset(source)
    if not np.all(np.diff(ds.x_edges)==1) or not np.all(np.diff(ds.y_edges)==1):
        raise ValueError('Packaged 512-cap input must be at native spatial resolution')
    output=ROOT/f'data/tofsims_demo_{args.target}.npz'
    if output==source: raise ValueError('Keep the native-resolution source intact')
    if output.exists() and not args.overwrite: raise FileExistsError('Use --overwrite for generated demo only')
    keep=ds.coverage[ds.y,ds.x]>0
    b,x,y,coverage,xe,ye=bin_counts(ds.matrix[keep],ds.x[keep],ds.y[keep],ds.shape,args.target)
    with np.load(source,allow_pickle=False) as z: arrays={k:z[k] for k in z.files}
    meta=dict(ds.metadata)
    meta.update(target=args.target,binned_shape=list(coverage.shape),spectral_shape_after=list(b.shape),
        effective_binning_factors=[ds.shape[0]/coverage.shape[0],ds.shape[1]/coverage.shape[1]],
        regenerated_from=source.name)
    meta['binning_note']='Integer edge partitions (variable widths); no crop/interpolation. Use stored edges for geometry.'
    arrays.update(indptr=b.indptr,indices=b.indices,values=b.data,pixel_x=x,pixel_y=y,coverage=coverage,
        x_edges=xe,y_edges=ye,shape=np.array(coverage.shape),metadata_json=np.array(json.dumps(meta)))
    if 'source_tissue_mask' in arrays:
        binary=arrays['source_tissue_mask']>0
        count=np.add.reduceat(np.add.reduceat(binary.astype(np.uint32),ye[:-1],axis=0),xe[:-1],axis=1)
        arrays['tissue_fraction']=count/(np.diff(ye)[:,None]*np.diff(xe)[None,:])
    np.testing.assert_array_equal(np.asarray(b.sum(axis=0)).ravel(),ds.spectrum())
    np.savez_compressed(output,**arrays)
    info_path=ROOT/'data/dataset_info.json';info=json.loads(info_path.read_text())
    variant={'file':output.name,'bytes':output.stat().st_size,'spatial_shape':list(coverage.shape),'spectral_shape':list(b.shape),
             'nnz':b.nnz,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'count_conservation':meta['validation']}
    info['variants']=[v for v in info['variants'] if v['file']!=output.name]+[variant]
    info_path.write_text(json.dumps(info,indent=2));print(variant)
