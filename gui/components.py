"""Pure Plotly figure builders, reusable outside NiceGUI."""
import plotly.graph_objects as go
from core.data_processing import image_level,scale_image,display_spectrum

def ion_figure(ds,image,mode='linear',cmap='Inferno',percentile=100,level=1,bounds=None,title='Ion map'):
    values,xe,ye=image_level(ds,image,level)
    z=scale_image(values,mode,percentile)
    fig=go.Figure(go.Heatmap(z=z.tolist(),x=xe.tolist(),y=ye.tolist(),colorscale=cmap,
        colorbar={'title':{'text':mode+' counts'}},hoverongaps=False))
    fig.update_layout(title=title,height=560,margin={'l':50,'r':30,'t':50,'b':50},
        xaxis_title='x (source pixel edges)',yaxis_title='y (source pixel edges)',
        xaxis={'range':[int(xe[0]),int(xe[-1])],'constrain':'domain'},
        yaxis={'range':[int(ye[-1]),int(ye[0])],'scaleanchor':'x','scaleratio':1,'constrain':'domain'},dragmode='pan')
    if bounds:
        x0,x1,y0,y1=bounds
        fig.add_shape(type='rect',x0=int(ds.x_edges[x0]),x1=int(ds.x_edges[x1]),
            y0=int(ds.y_edges[y0]),y1=int(ds.y_edges[y1]),line={'color':'cyan','width':2})
    return fig

def spectrum_figure(ds,counts,low,high,calibrated=False,log=False):
    x,y=display_spectrum(ds.mass_axis(calibrated),counts,low,high)
    fig=go.Figure(go.Scattergl(x=x.tolist(),y=y.tolist(),mode='lines',name='Counts',line={'width':1}))
    axis_label='acquisition QMS'
    if calibrated:
        axis_label='saved correction'+(' (QC failed)' if ds.metadata.get('calibration',{}).get('quality_pass') is False else '')
    fig.update_layout(title='Summed spectrum (display limited to 6,000 peak-preserving points)',height=450,
        xaxis_title='m/z — '+axis_label,
        yaxis_title='Counts',yaxis_type='log' if log else 'linear',dragmode='zoom',
        margin={'l':60,'r':30,'t':60,'b':50})
    return fig
