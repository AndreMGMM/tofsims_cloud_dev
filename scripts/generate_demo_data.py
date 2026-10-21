"""Convert inspected project CSR cache + companion QMS into the portable schema."""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.binning import bin_counts
from core.data_loader import ROOT

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()

def portable(value):
    if isinstance(value,dict): return {k:portable(v) for k,v in value.items()}
    if isinstance(value,list): return [portable(v) for v in value]
    if isinstance(value,str) and (':\\' in value or value.startswith('/')):
        return value.replace('\\','/').rsplit('/',1)[-1]
    return value

def generate(args):
    source=Path(args.source)
    axis_path=Path(args.qms) if args.qms else source.with_name(source.stem+'_qms.npy')
    mz=np.load(axis_path,allow_pickle=False)
    with np.load(source,allow_pickle=False) as z:
        needed={'shape','pixel_x','pixel_y','indptr','indices','values','n_bins'}
        if not needed<=set(z.files): raise ValueError('Expected project sparse-cache schema, not a dense cube or processed ion map')
        shape=tuple(int(v) for v in z['shape'])
        x,y=z['pixel_x'],z['pixel_y']
        values=z['values'];indices=z['indices'];indptr=z['indptr']
        if values.dtype.kind not in 'ui' or (values<0).any(): raise ValueError('Source is not nonnegative integer counts')
        if len(mz)!=int(z['n_bins'][0]): raise ValueError('QMS length disagrees with source n_bins')
        if not np.isfinite(mz).all() or not np.all(np.diff(mz)>0): raise ValueError('Invalid mass axis')
        if len(x)!=len(y) or len(indptr)!=len(x)+1 or len(shape)!=2: raise ValueError('Coordinate/CSR mismatch')
        if np.any(x>=shape[1]) or np.any(y>=shape[0]): raise ValueError('Coordinates outside shape')
        if len(np.unique(y.astype(np.int64)*shape[1]+x))!=len(x): raise ValueError('Duplicate source pixels')
        if int(values.max(initial=0))*len(values)>np.iinfo(np.uint64).max: raise OverflowError('Cannot guarantee uint64 accumulation safety')
        matrix=sparse.csr_matrix((values,indices,indptr),shape=(len(x),len(mz)))
        matrix.check_format(full_check=True)
        descriptors={k:{'shape':list(z[k].shape),'dtype':str(z[k].dtype)} for k in z.files}
        tile=z['tile_grid'] if 'tile_grid' in z else np.array([],dtype=np.uint32)
    calibration=json.loads(Path(args.calibration_summary).read_text()) if args.calibration_summary else {}
    coeffs=np.load(args.coefficients,allow_pickle=False) if args.coefficients else np.array([])
    if calibration.get('coefficients') is not None and not np.array_equal(coeffs,calibration['coefficients']):
        raise ValueError('Coefficient file disagrees with calibration summary')
    manifest=portable(json.loads(Path(args.manifest).read_text())) if args.manifest else {}
    with Path(args.peaks).open(encoding='utf-8-sig',newline='') if args.peaks else open(__file__,encoding='utf-8') as f:
        assignments=list(csv.DictReader(f,delimiter='\t')) if args.peaks else []
    mask=np.load(args.mask,allow_pickle=False) if args.mask else None
    if mask is not None and mask.shape!=shape: raise ValueError('Mask does not match source spatial frame')
    source_spectrum=np.asarray(matrix.sum(axis=0)).ravel()
    total=int(source_spectrum.sum())
    info={'sample':source.stem,'source_file':source.name,'source_bytes':source.stat().st_size,
          'axis_bytes':axis_path.stat().st_size,'source_sha256':digest(source),'qms_sha256':digest(axis_path),
          'source_spatial_shape':list(shape),'source_stored_pixels':len(x),'mass_channels':len(mz),
          'source_arrays':descriptors,'qms_dtype':str(mz.dtype),'total_counts':total,
          'acquisition':manifest,'calibration':calibration,'physical_pixel_size':None,
          'mass_axis_note':'Original QMS acquisition m/z unchanged. Saved polynomial correction is opt-in and retains its QC failure.',
          'ion_assignment_note':'Project reference candidates, including original confidence/QC fields; not newly identified ions.',
          'roi_note':'Associated automask retained in original coordinates and as fractional spatial coverage; no anatomical ROI masks found for selected sample.',
          'spatial_units':'source pixel edges; physical units unavailable',
          'source_tile_grid':tile.tolist(),'variants':[]}
    outdir=Path(args.output).resolve()
    if not outdir.is_relative_to(ROOT): raise ValueError('Outputs must remain inside the development package')
    outdir.mkdir(parents=True,exist_ok=True)
    for target in args.targets:
        output=outdir/f'tofsims_demo_{target}.npz'
        if output.exists() and not args.overwrite: raise FileExistsError(f'{output.name} exists; explicitly use --overwrite for generated demos only')
        b,bx,by,coverage,xe,ye=bin_counts(matrix,x,y,shape,target)
        bshape=coverage.shape
        if not np.array_equal(np.asarray(b.sum(axis=0)).ravel(),source_spectrum): raise AssertionError('Per-channel counts changed')
        # Independent coordinate accumulation checks spatial orientation and every TIC bin.
        expected=np.zeros(bshape,dtype=np.uint64)
        source_tic=np.asarray(matrix.sum(axis=1)).ravel()
        np.add.at(expected,(np.searchsorted(ye,y,side='right')-1,np.searchsorted(xe,x,side='right')-1),source_tic)
        if not np.array_equal(expected.ravel(),np.asarray(b.sum(axis=1)).ravel()): raise AssertionError('Spatial TIC mismatch')
        metadata={k:v for k,v in info.items() if k!='variants'}
        metadata.update({'target':target,'binned_shape':list(bshape),'aggregation':'sum integer counts (uint64)',
           'effective_binning_factors':[shape[0]/bshape[0],shape[1]/bshape[1]],
           'binning_note':'Integer edge partitions (variable widths); no crop/interpolation. Use stored edges for geometry.',
           'spectral_reduction':'none','spectral_shape_before':[len(x),len(mz)],'spectral_shape_after':list(b.shape),
           'validation':{'total_counts_equal':True,'every_mass_channel_equal':True,'every_spatial_tic_bin_equal':True}})
        arrays=dict(indptr=b.indptr,indices=b.indices,values=b.data,shape=np.array(bshape),pixel_x=bx,pixel_y=by,
                    mz_raw=mz,coverage=coverage,x_edges=xe,y_edges=ye,source_tile_grid=tile,
                    calibration_coefficients=coeffs,metadata_json=np.array(json.dumps(metadata)),
                    assignments_json=np.array(json.dumps(assignments)),source_summed_spectrum=source_spectrum)
        if mask is not None:
            binary=mask>0
            frac=np.add.reduceat(np.add.reduceat(binary.astype(np.uint32),ye[:-1],axis=0),xe[:-1],axis=1)
            arrays['source_tissue_mask']=mask
            arrays['tissue_fraction']=frac/(np.diff(ye)[:,None]*np.diff(xe)[None,:])
            arrays['tissue_acquired_source_pixels']=np.array(int(binary[y,x].sum()))
        np.savez_compressed(output,**arrays)
        variant={'file':output.name,'bytes':output.stat().st_size,'spatial_shape':list(bshape),
                 'spectral_shape':list(b.shape),'nnz':b.nnz,'sha256':digest(output),
                 'count_conservation':metadata['validation']}
        info['variants'].append(variant)
        print(json.dumps(variant))
    (outdir/'dataset_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',help='Project sparse count NPZ')
    for name in ('qms','manifest','peaks','coefficients','calibration-summary','mask'):
        p.add_argument('--'+name)
    p.add_argument('--targets',nargs='+',type=int,default=[256,512])
    p.add_argument('--output',default=str(ROOT/'data'))
    p.add_argument('--overwrite',action='store_true')
    return p

if __name__=='__main__': generate(parser().parse_args())
