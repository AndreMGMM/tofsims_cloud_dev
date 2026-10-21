"""Tablet-friendly exploratory GUI. Each browser client has isolated controls."""
import asyncio,io,json
from functools import lru_cache
import numpy as np
from nicegui import run,ui
from core.data_loader import ROOT,SparseDataset
from core.data_processing import roi_summary
from .components import ion_figure,spectrum_figure

@lru_cache(maxsize=1)
def load_dataset(path):
    return SparseDataset(path)

def spectrum_csv(ds,counts,calibrated):
    stream=io.StringIO()
    axis_name='raw'
    if calibrated:
        axis_name='saved_correction'+('_QC_FAILED' if ds.metadata.get('calibration',{}).get('quality_pass') is False else '')
    np.savetxt(stream,np.column_stack((ds.mass_axis(calibrated),counts)),delimiter=',',
        header='mz_'+axis_name+',counts',comments='',fmt=['%.12g','%.0f'])
    return stream.getvalue().encode()

@ui.page('/')
async def page():
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1">')
    ui.colors(primary='#155e75',secondary='#0f766e')
    with ui.header().classes('items-center'):
        ui.icon('science',size='md')
        ui.label('ToF-SIMS • Cloud development').classes('text-xl font-semibold')
    ui.label('Sparse spectra · original mass channels · browser workspace').classes('text-slate-600')
    state={'ds':None,'path':'data/tofsims_demo_256.npz'}
    lock=asyncio.Lock()
    status=ui.label('Loading included demo…')

    @ui.refreshable
    def body():
        ds=state['ds']
        if ds is None: return
        h,w=ds.shape
        with ui.tabs().classes('w-full') as tabs:
            labels=['Data Import','Ion Maps','Mass Spectra','ROI Analysis','Batch Processing','Export']
            sections={name:ui.tab(name) for name in labels}
        with ui.tab_panels(tabs,value=sections['Ion Maps']).classes('w-full'):
            with ui.tab_panel(sections['Data Import']):
                ui.label(ds.metadata.get('sample','Dataset')).classes('text-lg font-semibold')
                ui.label(f'{h} × {w} spatial bins | {len(ds.mz_raw):,} mass channels | {ds.matrix.nnz:,} stored nonzeros')
                ui.label(f'Acquired source pixels: {int(ds.coverage.sum()):,}; empty coverage stays transparent.')
                ui.label('Add converted NPZ files under data/ using the editor, then reload this page.')
                paths=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'data').rglob('*.npz'))
                choice=ui.select(paths,value=state['path'] if state['path'] in paths else paths[0],label='Packaged dataset').classes('w-full')
                async def import_data():
                    candidate=(ROOT/choice.value).resolve()
                    if not candidate.is_relative_to((ROOT/'data').resolve()):
                        ui.notify('Choose a dataset inside data/',type='negative');return
                    await change_dataset(candidate)
                ui.button('Load dataset',on_click=import_data)
                ui.label('Source caches need conversion with the companion QMS axis. See README.md.')
                with ui.expansion('Acquisition, reduction and calibration metadata').classes('w-full'):
                    ui.code(json.dumps(ds.metadata,indent=2),language='json').classes('w-full max-h-96 overflow-auto')
                ui.label(f'{len(ds.assignments)} reference ion candidates retained with their original confidence fields.')
            with ui.tab_panel(sections['Ion Maps']):
                ui.label('Reference assignments are candidates; confidence and calibration QC still apply.').classes('text-slate-600')
                options={'tic':'Total ion counts (TIC)','custom':'Custom mass window'}
                options.update({str(i):f"{p.get('Peak','?')} | {p.get('exact_mz','?')} | {p.get('assignment_qc_level','QC unavailable')}" for i,p in enumerate(ds.assignments)})
                ion=ui.select(options,value='tic',label='Ion / channel window',with_input=True).classes('w-full')
                with ui.row().classes('w-full items-end'):
                    low=ui.number('Window low m/z',value=78.877957,format='%.6f')
                    high=ui.number('Window high m/z',value=79.037957,format='%.6f')
                    failed=ds.metadata.get('calibration',{}).get('quality_pass') is False
                    corrected=ui.checkbox('Use saved mass correction'+(' (QC failed)' if failed else ''),value=False)
                    if not len(ds.coefficients): corrected.disable()
                with ui.row().classes('w-full items-end'):
                    scale=ui.select(['linear','sqrt','log1p'],value='sqrt',label='Intensity scaling')
                    cmap=ui.select(['Inferno','Viridis','Cividis','Magma','Gray'],value='Inferno',label='Colormap')
                    clip=ui.number('Upper display percentile',value=100,min=1,max=100)
                    level=ui.select({1:'Full detail',2:'2× display blocks',4:'4× display blocks'},value=1,label='Display detail')
                qc=ds.metadata.get('calibration',{})
                if qc.get('quality_pass') is False:
                    ui.label('Calibration QC FAILED: '+qc.get('failure_reason','See metadata.')).classes('text-red-700 font-semibold')
                assignment=ui.label('TIC includes every mass channel. Unacquired pixels are transparent.')
                chart=ui.plotly(ion_figure(ds,ds.ion_image(),mode='sqrt',title='Total ion counts')).classes('w-full')
                ui.label('Plots use source pixel edges; variable bin widths and image aspect ratio are retained. Display clipping never changes counts.')
                def selected_window():
                    key=ion.value
                    if key=='tic': return None,None,'Total ion counts'
                    if key=='custom': return float(low.value),float(high.value),'Custom mass window'
                    p=ds.assignments[int(key)]
                    return float(p['bin_min']),float(p['bin_max']),p.get('Peak','Reference candidate')
                async def update_map():
                    async with lock:
                        try:
                            a,b,title=selected_window()
                            image=await run.io_bound(ds.ion_image,a,b,corrected.value)
                            percentile=float(clip.value)
                            if not 1<=percentile<=100: raise ValueError('Percentile must be 1–100')
                            chart.figure=ion_figure(ds,image,scale.value,cmap.value,percentile,int(level.value),title=title)
                            chart.update()
                            if ion.value not in ('tic','custom'):
                                p=ds.assignments[int(ion.value)]
                                assignment.set_text(json.dumps(p,ensure_ascii=False))
                            else: assignment.set_text(f'{title}; raw counts in window {a} to {b}.')
                        except (ValueError,TypeError,KeyError) as e: ui.notify(str(e),type='negative')
                ui.button('Update ion map',on_click=update_map)
            with ui.tab_panel(sections['Mass Spectra']):
                ui.label('Zoom/pan with Plotly; set a narrow mass range and Update spectrum to retrieve full channel detail.')
                with ui.row():
                    spec_low=ui.number('Spectrum low m/z',value=float(ds.mz_raw[0]))
                    spec_high=ui.number('Spectrum high m/z',value=float(ds.mz_raw[-1]))
                    spec_log=ui.checkbox('Log count axis')
                spectrum=ui.plotly(spectrum_figure(ds,ds.spectrum(),float(ds.mz_raw[0]),float(ds.mz_raw[-1]))).classes('w-full')
                async def update_spectrum():
                    async with lock:
                        try:
                            fig=await run.io_bound(spectrum_figure,ds,ds.spectrum(),float(spec_low.value),float(spec_high.value),corrected.value,spec_log.value)
                            spectrum.figure=fig;spectrum.update()
                        except (ValueError,TypeError) as e: ui.notify(str(e),type='negative')
                ui.button('Update spectrum',on_click=update_spectrum)
                ui.label('Peak-preserving display reduction is visual only. Every original mass position remains in the dataset and CSV exports.')
            with ui.tab_panel(sections['ROI Analysis']):
                ui.label('Rectangle in binned pixel indices; end bounds are exclusive. Numerical controls work on touch screens.')
                with ui.row():
                    x0=ui.number('x start',value=0,min=0,max=w-1,step=1,precision=0)
                    x1=ui.number('x end (exclusive)',value=w,min=1,max=w,step=1,precision=0)
                    y0=ui.number('y start',value=0,min=0,max=h-1,step=1,precision=0)
                    y1=ui.number('y end (exclusive)',value=h,min=1,max=h,step=1,precision=0)
                roi_chart=ui.plotly(ion_figure(ds,ds.ion_image(),bounds=(0,w,0,h),title='ROI on TIC')).classes('w-full')
                roi_label=ui.label('Whole image selected. Click Analyze ROI to calculate counts and spectrum.')
                roi_plot=ui.plotly(spectrum_figure(ds,ds.spectrum(),float(ds.mz_raw[0]),float(ds.mz_raw[-1]))).classes('w-full')
                def bounds():
                    values=[v.value for v in (x0,x1,y0,y1)]
                    if any(v is None or float(v)!=int(v) for v in values): raise ValueError('ROI bounds must be integers')
                    return tuple(int(v) for v in values)
                async def analyze_roi():
                    async with lock:
                        try:
                            box=bounds();summary,counts=await run.io_bound(roi_summary,ds,box)
                            roi_label.set_text(json.dumps(summary))
                            roi_chart.figure=ion_figure(ds,ds.ion_image(),bounds=box,title='ROI on TIC');roi_chart.update()
                            roi_plot.figure=spectrum_figure(ds,counts,float(spec_low.value),float(spec_high.value),corrected.value,spec_log.value);roi_plot.update()
                        except (ValueError,TypeError) as e: ui.notify(str(e),type='negative')
                ui.button('Analyze ROI',on_click=analyze_roi)
                ui.label('Tissue mask and fractional coverage are preserved in NPZ. Anatomical labels and sub-bin ROI recovery are not implemented.')
            with ui.tab_panel(sections['Batch Processing']):
                ui.label('Planned: queued multi-sample jobs, cancellation, progress and resumable outputs.')
                ui.label('Current demo generation and validation are available as terminal scripts.')
            with ui.tab_panel(sections['Export']):
                ui.label('CSV exports contain analytical counts, without display scaling, clipping or spectral decimation.')
                async def export_spectrum(roi=False):
                    async with lock:
                        try:
                            counts=await run.io_bound(ds.spectrum,bounds() if roi else None)
                            payload=await run.io_bound(spectrum_csv,ds,counts,corrected.value)
                            ui.download(payload,filename='roi_spectrum.csv' if roi else 'summed_spectrum.csv')
                        except (ValueError,TypeError) as e: ui.notify(str(e),type='negative')
                async def export_image():
                    async with lock:
                        try:
                            a,b,title=selected_window();image=await run.io_bound(ds.ion_image,a,b,corrected.value)
                            def make_csv():
                                yy,xx=np.indices(ds.shape);stream=io.StringIO()
                                np.savetxt(stream,np.column_stack((xx.ravel(),yy.ravel(),image.ravel(),ds.coverage.ravel())),delimiter=',',
                                    header='x_bin,y_bin,raw_counts,acquired_source_pixels',comments='',fmt=['%d','%d','%.0f','%d'])
                                return stream.getvalue().encode()
                            payload=await run.io_bound(make_csv)
                            ui.download(payload,filename='ion_image_counts.csv')
                            ui.download(json.dumps({'ion':title,'low':a,'high':b,'saved_correction':corrected.value,
                                'calibration_qc':qc,'x_edges':ds.x_edges.tolist(),'y_edges':ds.y_edges.tolist()}).encode(),filename='ion_image_provenance.json')
                        except (ValueError,TypeError) as e: ui.notify(str(e),type='negative')
                ui.button('Download summed spectrum CSV',on_click=lambda:export_spectrum(False))
                ui.button('Download ROI spectrum CSV',on_click=lambda:export_spectrum(True))
                ui.button('Download selected ion counts + provenance',on_click=export_image)
                ui.button('Download dataset metadata JSON',on_click=lambda:ui.download(json.dumps(ds.metadata,indent=2).encode(),filename='dataset_metadata.json'))

    async def change_dataset(path):
        status.set_text('Loading compressed sparse dataset…')
        try:
            if path.stat().st_size>100*1024*1024: raise ValueError('Demo importer limit is 100 MiB; use a future chunked backend for larger data')
            async with lock:
                state['ds']=await run.io_bound(load_dataset,str(path))
                state['path']=path.relative_to(ROOT).as_posix()
                # Warm expensive shared products outside the event loop.
                await run.io_bound(state['ds'].ion_image)
                await run.io_bound(state['ds'].spectrum)
                body.refresh()
            status.set_text('Ready • '+path.name)
        except Exception as e:
            status.set_text('Could not load dataset: '+str(e))
    body()
    await change_dataset(ROOT/'data/tofsims_demo_256.npz')
