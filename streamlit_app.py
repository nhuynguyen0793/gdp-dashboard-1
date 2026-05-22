import streamlit as st
import pandas as pd
import math
from pathlib import Path

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.
import streamlit as st
import pandas as pd
import math
from pathlib import Path
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from branca.colormap import LinearColormap

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode.
)

# ------------------------------------------------------------------
# Declare some useful functions.

VN2000_PROJ = (
    '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 '
    '+x_0=500000 +y_0=0 +ellps=WGS84 '
    '+towgs84=-191.90441429,-39.30318279,-111.45032835,'
    '-0.00928836,0.01975479,-0.00427372,0.252906278 '
    '+units=m +no_defs'
)

DATA_DIR = Path(__file__).parent / 'data'

@st.cache_data
def load_geodata() -> gpd.GeoDataFrame:
    """Doc shapefile, chuyen ve WGS84, chuan hoa kieu du lieu."""
    gdf = gpd.read_file(DATA_DIR / 'NewHCMC_RanhPX.shp', encoding='utf-8')
    gdf = gdf.set_crs(VN2000_PROJ, allow_override=True).to_crs('EPSG:4326')
    for col in ['DanSo', 'DienTich', 'MatDo']:
        gdf[col] = pd.to_numeric(gdf[col], errors='coerce')
    return gdf


def make_choropleth(gdf: gpd.GeoDataFrame, metric: str) -> folium.Map:
    """Ve ban do choropleth theo chi tieu da chon."""
    META = {
        'DanSo':    ('Dan so (nguoi)',       'YlOrRd'),
        'DienTich': ('Dien tich (km2)',      'YlGn'),
        'MatDo':    ('Mat do (nguoi/km2)',   'OrRd'),
    }
    label, palette = META[metric]

    cy = gdf.geometry.centroid.y.mean()
    cx = gdf.geometry.centroid.x.mean()
    m = folium.Map(
        location=[cy, cx], zoom_start=10,
        tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attr='OpenStreetMap & CARTO',
    )

    vals   = gdf[metric].dropna()
    vmin, vmax = vals.min(), vals.max()
    cmap   = LinearColormap(
        ['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026']
        if palette == 'YlOrRd' else
        ['#ffffcc','#c7e9b4','#7fcdbb','#2c7fb8','#253494']
        if palette == 'YlGn' else
        ['#fff7ec','#fee8c8','#fc8d59','#d7301f','#7f0000'],
        vmin=vmin, vmax=vmax,
    )
    cmap.caption = label
    cmap.add_to(m)

    fmt = {
        'DanSo':    lambda v: f'{v:,.0f} nguoi',
        'DienTich': lambda v: f'{v:,.2f} km2',
        'MatDo':    lambda v: f'{v:,.0f} ng/km2',
    }

    def style(feat):
        try:
            c = cmap(float(feat['properties'][metric]))
        except Exception:
            c = '#444'
        return {'fillColor': c, 'color': '#fff', 'weight': 0.7, 'fillOpacity': 0.78}

    def highlight(_):
        return {'fillColor': '#fff', 'color': '#fff', 'weight': 2, 'fillOpacity': 0.4}

    for _, row in gdf.iterrows():
        name = row.get('TenDVHC', '')
        pop  = row.get('DanSo')
        area = row.get('DienTich')
        dens = row.get('MatDo')
        tip  = folium.Tooltip(f"""
            <div style='font-family:sans-serif;min-width:170px'>
                <b style='font-size:13px'>{name}</b>
                <hr style='margin:4px 0'>
                <table style='font-size:12px;width:100%'>
                  <tr><td>Dan so</td>   <td align='right'><b>{pop:,.0f}</b> nguoi</td></tr>
                  <tr><td>Dien tich</td><td align='right'><b>{area:,.2f}</b> km2</td></tr>
                  <tr><td>Mat do</td>   <td align='right'><b>{dens:,.0f}</b> ng/km2</td></tr>
                </table>
            </div>""", sticky=True)
        feat = {
            'type': 'Feature',
            'properties': {c: row[c] for c in gdf.columns if c != 'geometry'},
            'geometry': row.geometry.__geo_interface__,
        }
        folium.GeoJson(feat, style_function=style,
                       highlight_function=highlight, tooltip=tip).add_to(m)

        # Nhan ten phuong
        folium.Marker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            icon=folium.DivIcon(
                html=f'<div style="font-size:8px;color:#fff;'
                     f'text-shadow:0 0 3px #000;font-weight:600;'
                     f'white-space:nowrap">{str(name)[:22]}</div>',
                icon_size=(130, 14), icon_anchor=(65, 7),
            )
        ).add_to(m)

    return m


# ------------------------------------------------------------------
# Draw the actual page

st.markdown('# 🗺️ Truc quan Dan so TP. Ho Chi Minh')
st.markdown('Ranh gioi **168 phuong/xa** — du lieu dia chinh HCMC')
st.divider()

# Doc du lieu
gdf = load_geodata()

# ── KPI ROW ──────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric('Tong dan so',   f"{gdf['DanSo'].sum():,.0f}",   'nguoi')
col2.metric('Tong dien tich', f"{gdf['DienTich'].sum():,.1f}", 'km2')
col3.metric('Mat do trung binh', f"{gdf['MatDo'].mean():,.0f}", 'nguoi/km2')
col4.metric('So phuong/xa',  f"{len(gdf):,}", 'don vi')

st.divider()

# ── TABS ─────────────────────────────────────────────────────────
tab_map, tab_charts, tab_rank, tab_data = st.tabs([
    '🗺️ Ban do', '📊 Bieu do', '🏆 Xep hang', '📋 Du lieu'
])

# ── TAB: BAN DO ───────────────────────────────────────────────────
with tab_map:
    metric = st.radio(
        'To mau theo chi tieu:',
        options=['MatDo', 'DanSo', 'DienTich'],
        format_func=lambda x: {'MatDo':'Mat do dan so','DanSo':'Dan so','DienTich':'Dien tich'}[x],
        horizontal=True,
    )
    with st.spinner('Dang ve ban do...'):
        fm = make_choropleth(gdf, metric)
        st_folium(fm, use_container_width=True, height=620)

# ── TAB: BIEU DO ──────────────────────────────────────────────────
with tab_charts:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('#### Phan phoi Mat do Dan so')
        fig = px.histogram(
            gdf, x='MatDo', nbins=30,
            labels={'MatDo': 'Mat do (nguoi/km2)', 'count': 'So phuong/xa'},
            color_discrete_sequence=['#4e9af1'],
            template='plotly_dark',
        )
        fig.update_layout(paper_bgcolor='#0f1117', plot_bgcolor='#0f1117',
                          margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('#### Dan so vs Dien tich')
        fig2 = px.scatter(
            gdf, x='DienTich', y='DanSo',
            size='MatDo', color='MatDo',
            hover_name='TenDVHC',
            color_continuous_scale='YlOrRd',
            labels={'DienTich':'Dien tich (km2)','DanSo':'Dan so','MatDo':'Mat do'},
            template='plotly_dark',
        )
        fig2.update_layout(paper_bgcolor='#0f1117', plot_bgcolor='#0f1117',
                           margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('#### Dan so & Mat do theo Top 20 phuong/xa dong dan nhat')
    top20 = gdf.nlargest(20, 'DanSo')[['TenDVHC','DanSo','MatDo','DienTich']].copy()
    fig3 = px.bar(
        top20, x='TenDVHC', y='DanSo',
        color='MatDo', color_continuous_scale='OrRd',
        labels={'TenDVHC':'','DanSo':'Dan so (nguoi)','MatDo':'Mat do'},
        template='plotly_dark', height=380,
    )
    fig3.update_layout(paper_bgcolor='#0f1117', plot_bgcolor='#0f1117',
                       xaxis_tickangle=-45, margin=dict(b=120, t=10))
    st.plotly_chart(fig3, use_container_width=True)

# ── TAB: XEP HANG ─────────────────────────────────────────────────
with tab_rank:
    top_n = st.slider('Hien thi Top N', 5, 30, 15)
    r1, r2, r3 = st.columns(3)

    def hbar(col, title, cscale):
        df = gdf[['TenDVHC', col]].dropna().nlargest(top_n, col)
        fig = px.bar(
            df, x=col, y='TenDVHC', orientation='h',
            color=col, color_continuous_scale=cscale,
            labels={col: title, 'TenDVHC': ''},
            template='plotly_dark', height=420,
        )
        fig.update_layout(
            paper_bgcolor='#0f1117', plot_bgcolor='#0f1117',
            margin=dict(t=10, b=10), coloraxis_showscale=False,
            yaxis={'categoryorder': 'total ascending'},
        )
        return fig

    with r1:
        st.markdown(f'#### Top {top_n} Dan so')
        st.plotly_chart(hbar('DanSo', 'Dan so (nguoi)', 'Blues'), use_container_width=True)
    with r2:
        st.markdown(f'#### Top {top_n} Dien tich')
        st.plotly_chart(hbar('DienTich', 'Dien tich (km2)', 'Greens'), use_container_width=True)
    with r3:
        st.markdown(f'#### Top {top_n} Mat do')
        st.plotly_chart(hbar('MatDo', 'Mat do (nguoi/km2)', 'Oranges'), use_container_width=True)

# ── TAB: DU LIEU ──────────────────────────────────────────────────
with tab_data:
    df_show = gdf[['TenDVHC','DanSo','DienTich','MatDo']].copy().reset_index(drop=True)
    df_show.columns = ['Phuong/Xa', 'Dan so', 'Dien tich (km2)', 'Mat do (ng/km2)']

    q = st.text_input('🔍 Tim kiem ten phuong/xa', '')
    if q:
        df_show = df_show[df_show['Phuong/Xa'].str.contains(q, case=False, na=False)]

    sort_by = st.selectbox('Sap xep theo', df_show.columns[1:].tolist(), index=2)
    df_show = df_show.sort_values(sort_by, ascending=False)

    st.dataframe(
        df_show.style.background_gradient(
            subset=['Dan so', 'Dien tich (km2)', 'Mat do (ng/km2)'], cmap='YlOrRd'
        ),
        use_container_width=True, height=480,
    )
    st.download_button(
        '⬇️ Tai xuong CSV',
        data=df_show.to_csv(index=False).encode('utf-8-sig'),
        file_name='hcmc_danso.csv',
        mime='text/csv',
    )

