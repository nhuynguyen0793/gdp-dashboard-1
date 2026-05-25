import streamlit as st
import pandas as pd
from pathlib import Path
import geopandas as gpd
import folium
from folium import Choropleth, GeoJsonTooltip
from streamlit_folium import st_folium
import plotly.express as px
import json

# ── CẤU HÌNH TRANG ────────────────────────────────────────────────
import streamlit as st
import pandas as pd
from pathlib import Path
import geopandas as gpd
import folium
from folium import Choropleth, GeoJsonTooltip
from streamlit_folium import st_folium
import plotly.express as px
import json
import unicodedata
import urllib.parse
from streamlit_searchbox import st_searchbox

# ── CẤU HÌNH TRANG ────────────────────────────────────────────────
st.set_page_config(
    page_title="Bản đồ Dân số HCMC",
    page_icon=":earth_americas:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 0 !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
.kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 10px 0 16px 0;
}
.kpi-card {
    background: linear-gradient(135deg,#f0f4ff,#e8edf8);
    border: 1px solid rgba(78,154,241,0.3);
    border-radius: 14px;
    padding: 14px 18px;
    text-align: center;
}
.kpi-val {
    font-family: 'DM Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #1a56db;
    line-height: 1.1;
}
.kpi-lbl {
    font-size: 0.7rem;
    color: #555a6e;
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.kpi-sub { font-size: 0.67rem; color: #888; margin-top: 2px; }
.stTabs [data-baseweb="tab-list"] {
    gap: 6px; background: #f0f4ff;
    border-radius: 10px; padding: 4px 6px;
}
.stTabs [data-baseweb="tab"] {
    color: #555a6e; font-size: .88rem;
    font-weight: 500; border-radius: 8px; padding: 6px 16px;
}
.stTabs [aria-selected="true"] {
    color: #1a56db !important;
    background: rgba(26,86,219,0.1) !important;
}
.page-title { font-size:1.5rem; font-weight:700; color:#1a1a2e; margin:0 0 2px 0; }
.page-sub   { font-size:.83rem; color:#666; margin-bottom:10px; }
</style>
""", unsafe_allow_html=True)

# ── HẰNG SỐ ───────────────────────────────────────────────────────
VN2000_PROJ = (
    "+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 "
    "+x_0=500000 +y_0=0 +ellps=WGS84 "
    "+towgs84=-191.90441429,-39.30318279,-111.45032835,"
    "-0.00928836,0.01975479,-0.00427372,0.252906278 "
    "+units=m +no_defs"
)
DATA_DIR = Path(__file__).parent / "data"

METRIC_CFG = {
    "MatDo":    {"label": "Mật độ dân số (người/km²)", "cmap": "YlOrRd", "fmt": "{:,.0f}"},
    "DanSo":    {"label": "Dân số (người)",             "cmap": "Blues",  "fmt": "{:,.0f}"},
    "DienTich": {"label": "Diện tích (km²)",            "cmap": "YlGn",   "fmt": "{:,.2f}"},
}

# ── ĐỌC DỮ LIỆU (cache) ───────────────────────────────────────────
@st.cache_data
def load_geodata():
    gdf = gpd.read_file(DATA_DIR / "NewHCMC_RanhPX.shp", encoding="utf-8")
    gdf = gdf.set_crs(VN2000_PROJ, allow_override=True).to_crs("EPSG:4326")
    for col in ["DanSo", "DienTich", "MatDo"]:
        gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
    gdf["id"] = gdf.index.astype(str)

    # Đọc trường học
    df_th = pd.read_excel(DATA_DIR / "Truong_Hoc.xlsx")
    df_th = df_th.rename(columns={
        df_th.columns[1]: "TenDVHC",
        df_th.columns[2]: "TenTruong",
        df_th.columns[3]: "LinkTruong",
    })[["TenDVHC","TenTruong","LinkTruong"]]

    # Đọc bệnh viện
    df_bv = pd.read_excel(DATA_DIR / "Benh_Vien.xlsx",
                          sheet_name=0)
    df_bv = df_bv.rename(columns={
        df_bv.columns[1]: "TenDVHC",
        df_bv.columns[2]: "TenBenhVien",
        df_bv.columns[3]: "DiaChiBV",
        df_bv.columns[4]: "LinkBV",
    })[["TenDVHC","TenBenhVien","DiaChiBV","LinkBV"]]

    # Join vào gdf theo tên phường/xã
    gdf = gdf.merge(df_th, on="TenDVHC", how="left")
    gdf = gdf.merge(df_bv, on="TenDVHC", how="left")
    return gdf

@st.cache_data
def get_geojson_str(_gdf):
    """Cache GeoJSON string — chỉ serialize 1 lần."""
    cols = ["id","TenDVHC","DanSo","DienTich","MatDo",
            "TenTruong","LinkTruong","TenBenhVien","DiaChiBV","LinkBV","geometry"]
    cols = [c for c in cols if c in _gdf.columns]
    return _gdf[cols].to_json(ensure_ascii=False)

gdf = load_geodata()
geojson_str = get_geojson_str(gdf)

# ── HÀM VẼ BẢN ĐỒ NỀN + CHOROPLETH (cache được) ─────────────────
@st.cache_data
def make_base_map(metric: str) -> str:
    """
    Tạo bản đồ nền + choropleth, trả về HTML string để cache.
    Hàm này CHỈ chạy lại khi đổi metric — không phụ thuộc focus_name.
    """
    cfg = METRIC_CFG[metric]

    m = folium.Map(
        location=[10.776, 106.700],
        zoom_start=11,
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap © CARTO",
        prefer_canvas=True,
    )

    Choropleth(
        geo_data=geojson_str,
        data=gdf[["id", metric]],
        columns=["id", metric],
        key_on="feature.properties.id",
        fill_color=cfg["cmap"],
        fill_opacity=0.75,
        line_opacity=0.5,
        line_color="#666",
        line_weight=0.6,
        legend_name=cfg["label"],
        nan_fill_color="#eee",
        highlight=False,   # tắt highlight ở đây, để tooltip layer xử lý
    ).add_to(m)

    # Tooltip layer trong suốt — hover hiển thị thông tin
    folium.GeoJson(
        geojson_str,
        style_function=lambda _: {
            "fillColor": "transparent",
            "color":     "transparent",
            "weight":    0,
        },
        highlight_function=lambda _: {
            "fillColor": "#1a56db",
            "color":     "#1a56db",
            "weight":    2,
            "fillOpacity": 0.12,
        },
        tooltip=GeoJsonTooltip(
            fields=["TenDVHC", "DanSo", "DienTich", "MatDo"],
            aliases=["Phường/Xã:", "Dân số:", "Diện tích (km²):", "Mật độ (ng/km²):"],
            localize=True,
            sticky=True,
            style=(
                "font-family:Inter,sans-serif;"
                "font-size:13px;"
                "padding:8px 10px;"
                "border-radius:8px;"
            ),
        ),
    ).add_to(m)

    return m._repr_html_()   # trả HTML string — cache được


def make_map(metric: str, focus_name: str) -> folium.Map:
    """
    Ghép bản đồ nền (từ cache) + layer highlight phường được chọn.
    Khi đổi phường: chỉ vẽ lại 1 polygon nhỏ, không render lại toàn bộ.
    """
    cfg = METRIC_CFG[metric]

    # Bbox toàn bộ dữ liệu [minx, miny, maxx, maxy]
    b = gdf.total_bounds

    m = folium.Map(
        location=[(b[1]+b[3])/2, (b[0]+b[2])/2],
        zoom_start=10,
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap © CARTO",
        prefer_canvas=True,
    )

    # Toàn cảnh: fit vừa màn hình theo đúng extent dữ liệu
    if focus_name == "— Toàn TP. HCM —":
        m.fit_bounds([[b[1], b[0]], [b[3], b[2]]], padding=[10, 10])

    # Choropleth toàn bộ
    Choropleth(
        geo_data=geojson_str,
        data=gdf[["id", metric]],
        columns=["id", metric],
        key_on="feature.properties.id",
        fill_color=cfg["cmap"],
        fill_opacity=0.75,
        line_opacity=0.5,
        line_color="#666",
        line_weight=0.6,
        legend_name=cfg["label"],
        nan_fill_color="#eee",
        highlight=False,
    ).add_to(m)

    # ── Tooltip + Popup layer (hover + click) ──
    def popup_html(props):
        name     = props.get("TenDVHC", "")
        dan_so   = props.get("DanSo", "")
        dien_tich= props.get("DienTich", "")
        mat_do   = props.get("MatDo", "")
        truong   = props.get("TenTruong", "") or "Chưa có dữ liệu"
        link_th  = props.get("LinkTruong", "") or ""
        benh_vien= props.get("TenBenhVien", "") or "Chưa có dữ liệu"
        dia_chi  = props.get("DiaChiBV", "") or ""
        link_bv  = props.get("LinkBV", "") or ""

        try: dan_so_s   = f"{float(dan_so):,.0f}"
        except: dan_so_s = str(dan_so)
        try: dien_tich_s = f"{float(dien_tich):,.2f}"
        except: dien_tich_s = str(dien_tich)
        try: mat_do_s   = f"{float(mat_do):,.0f}"
        except: mat_do_s = str(mat_do)

        # Link Google Maps phường/xã
        maps_link = f"https://www.google.com/maps/search/{urllib.parse.quote(name + ' TP HCM')}"

        truong_html = (
            f'<a href="{link_th}" target="_blank" style="color:#1a56db;text-decoration:none">'
            f'📍 {truong}</a>'
            if link_th else truong
        )
        bv_html = (
            f'<a href="{link_bv}" target="_blank" style="color:#e63946;text-decoration:none">'
            f'📍 {benh_vien}</a>'
            if link_bv else benh_vien
        )

        return f"""
        <div style="font-family:Inter,sans-serif;min-width:280px;max-width:340px;font-size:12.5px">
            <div style="background:#1a56db;color:#fff;padding:8px 12px;border-radius:6px 6px 0 0;
                        font-size:14px;font-weight:700">
                📍 {name}
                &nbsp;<a href="{maps_link}" target="_blank"
                   style="color:#a8d4ff;font-size:11px;font-weight:400">
                   🗺️ Google Maps</a>
            </div>
            <div style="padding:10px 12px;background:#fff;border:1px solid #e0e7ff;
                        border-top:none;border-radius:0 0 6px 6px">

                <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
                  <tr style="background:#f0f4ff">
                    <td style="padding:4px 6px;color:#555;white-space:nowrap">👥 Dân số</td>
                    <td style="padding:4px 6px;font-weight:600;color:#1a1a2e">{dan_so_s} người</td>
                  </tr>
                  <tr>
                    <td style="padding:4px 6px;color:#555;white-space:nowrap">📐 Diện tích</td>
                    <td style="padding:4px 6px;font-weight:600;color:#1a1a2e">{dien_tich_s} km²</td>
                  </tr>
                  <tr style="background:#f0f4ff">
                    <td style="padding:4px 6px;color:#555;white-space:nowrap">🏘️ Mật độ</td>
                    <td style="padding:4px 6px;font-weight:600;color:#1a1a2e">{mat_do_s} ng/km²</td>
                  </tr>
                </table>

                <div style="margin-bottom:6px;padding:6px 8px;background:#fffbf0;
                            border-left:3px solid #f59e0b;border-radius:0 4px 4px 0">
                    <div style="font-size:10px;color:#92400e;font-weight:600;
                                text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px">
                        🏫 Trường học
                    </div>
                    <div style="color:#1a1a2e">{truong_html}</div>
                </div>

                <div style="padding:6px 8px;background:#fff5f5;
                            border-left:3px solid #e63946;border-radius:0 4px 4px 0">
                    <div style="font-size:10px;color:#9b1c1c;font-weight:600;
                                text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px">
                        🏥 Bệnh viện / Cơ sở y tế
                    </div>
                    <div style="color:#1a1a2e;margin-bottom:2px">{bv_html}</div>
                    {f'<div style="font-size:11px;color:#666">📌 {dia_chi}</div>' if dia_chi else ''}
                </div>
            </div>
        </div>
        """

    # Google Maps pin icon SVG (inline, dùng lại nhiều chỗ)
    GMAP_PIN = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="18" viewBox="0 0 24 30" '
        'style="vertical-align:middle;margin-right:3px">'
        '<path d="M12 0C7.6 0 4 3.6 4 8c0 6 8 16 8 16s8-10 8-16c0-4.4-3.6-8-8-8z" fill="#EA4335"/>'
        '<circle cx="12" cy="8" r="3" fill="#fff"/>'
        '</svg>'
    )

    # ── Tooltip hiển thị đầy đủ popup khi hover ──
    def tooltip_html(props):
        name      = props.get("TenDVHC", "")
        dan_so    = props.get("DanSo", "")
        dien_tich = props.get("DienTich", "")
        mat_do    = props.get("MatDo", "")
        truong    = props.get("TenTruong", "") or "Chưa có dữ liệu"
        link_th   = props.get("LinkTruong", "") or ""
        benh_vien = props.get("TenBenhVien", "") or "Chưa có dữ liệu"
        dia_chi   = props.get("DiaChiBV", "") or ""
        link_bv   = props.get("LinkBV", "") or ""

        try: dan_so_s    = f"{float(dan_so):,.0f}"
        except: dan_so_s = str(dan_so)
        try: dien_tich_s = f"{float(dien_tich):,.2f}"
        except: dien_tich_s = str(dien_tich)
        try: mat_do_s    = f"{float(mat_do):,.0f}"
        except: mat_do_s = str(mat_do)

        maps_link = f"https://www.google.com/maps/search/{urllib.parse.quote(name + ' TP HCM')}"

        truong_html = (
            f'<a href="{link_th}" target="_blank" '
            f'style="color:#1a56db;text-decoration:none">{GMAP_PIN}{truong}</a>'
            if link_th else truong
        )
        bv_html = (
            f'<a href="{link_bv}" target="_blank" '
            f'style="color:#e63946;text-decoration:none">{GMAP_PIN}{benh_vien}</a>'
            if link_bv else benh_vien
        )

        return f"""
        <div style="font-family:Inter,sans-serif;width:300px;max-width:300px;
                    font-size:12.5px;box-sizing:border-box;overflow:hidden">
            <div style="background:#1a56db;color:#fff;padding:8px 12px;
                        border-radius:6px 6px 0 0;font-size:13px;font-weight:700;
                        display:flex;align-items:center;justify-content:space-between;
                        gap:6px;overflow:hidden">
                <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">
                    {GMAP_PIN.replace('fill="#EA4335"','fill="#fff"').replace('fill="#fff"','fill="#1a56db"',1)} {name}
                </span>
                <a href="{maps_link}" target="_blank"
                   style="color:#a8d4ff;font-size:11px;font-weight:400;
                          white-space:nowrap;flex-shrink:0">
                   {GMAP_PIN.replace('fill="#EA4335"','fill="#a8d4ff"')} Google Maps
                </a>
            </div>
            <div style="padding:10px 12px;background:#fff;border:1px solid #e0e7ff;
                        border-top:none;border-radius:0 0 6px 6px;overflow:hidden">
                <table style="width:100%;border-collapse:collapse;margin-bottom:8px;table-layout:fixed">
                  <tr style="background:#f0f4ff">
                    <td style="padding:4px 6px;color:#555;white-space:nowrap;width:95px">👥 Dân số</td>
                    <td style="padding:4px 6px;font-weight:600;color:#1a1a2e">{dan_so_s} người</td>
                  </tr>
                  <tr>
                    <td style="padding:4px 6px;color:#555;white-space:nowrap">📐 Diện tích</td>
                    <td style="padding:4px 6px;font-weight:600;color:#1a1a2e">{dien_tich_s} km²</td>
                  </tr>
                  <tr style="background:#f0f4ff">
                    <td style="padding:4px 6px;color:#555;white-space:nowrap">🏘️ Mật độ</td>
                    <td style="padding:4px 6px;font-weight:600;color:#1a1a2e">{mat_do_s} ng/km²</td>
                  </tr>
                </table>
                <div style="margin-bottom:6px;padding:6px 8px;background:#fffbf0;
                            border-left:3px solid #f59e0b;border-radius:0 4px 4px 0">
                    <div style="font-size:10px;color:#92400e;font-weight:600;
                                text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">
                        🏫 Trường học
                    </div>
                    <div style="color:#1a1a2e;word-break:break-word">{truong_html}</div>
                </div>
                <div style="padding:6px 8px;background:#fff5f5;
                            border-left:3px solid #e63946;border-radius:0 4px 4px 0">
                    <div style="font-size:10px;color:#9b1c1c;font-weight:600;
                                text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">
                        🏥 Bệnh viện / Cơ sở y tế
                    </div>
                    <div style="color:#1a1a2e;margin-bottom:2px;word-break:break-word">{bv_html}</div>
                    {f'<div style="font-size:11px;color:#666;word-break:break-word">📌 {dia_chi}</div>' if dia_chi else ''}
                </div>
            </div>
        </div>
        """

    gj_data = json.loads(geojson_str)
    for feat in gj_data["features"]:
        props = feat["properties"]
        name  = props.get("TenDVHC", "")
        folium.GeoJson(
            feat,
            style_function=lambda _: {
                "fillColor": "transparent",
                "color":     "transparent",
                "weight":    0,
            },
            highlight_function=lambda _: {
                "fillColor": "#1a56db",
                "color":     "#1a56db",
                "weight":    2,
                "fillOpacity": 0.12,
            },
            # Hover: chỉ hiện tên phường/xã
            tooltip=folium.Tooltip(
                f'<span style="font-family:Inter,sans-serif;font-size:13px;'
                f'font-weight:700;color:#1a1a2e">{name}</span>',
                sticky=False,
            ),
            # Click: hiện popup đầy đủ
            popup=folium.Popup(
                folium.Html(tooltip_html(props), script=True),
                max_width=320,
                lazy=True,   # chỉ render khi click — tiết kiệm bộ nhớ
            ),
        ).add_to(m)

    # ── Highlight + fit_bounds phường được chọn ──
    if focus_name != "— Toàn TP. HCM —":
        sel = gdf[gdf["TenDVHC"] == focus_name]
        if not sel.empty:
            geom = sel.geometry.iloc[0]
            bounds = geom.bounds  # (minx, miny, maxx, maxy)

            # fit_bounds để polygon vừa màn hình
            m.fit_bounds(
                [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
                padding=[40, 40],
            )

            # Viền đỏ nổi bật + tooltip đầy đủ cho polygon được chọn
            sel_row = gdf[gdf["TenDVHC"] == focus_name].iloc[0]
            # Dùng pandas để convert numpy types → Python native (int64→int, float64→float)
            sel_props = (
                gdf[gdf["TenDVHC"] == focus_name]
                .drop(columns="geometry")
                .astype(object)        # ép về object dtype trước
                .iloc[0]
                .where(lambda x: x.notna(), other=None)   # NaN → None
                .to_dict()
            )
            sel_feat = {
                "type": "Feature",
                "properties": sel_props,
                "geometry": sel.geometry.iloc[0].__geo_interface__,
            }
            folium.GeoJson(
                sel_feat,
                style_function=lambda _: {
                    "fillColor": "rgba(230,57,70,0.08)",
                    "color":     "#e63946",
                    "weight":    3.5,
                    "fillOpacity": 0.08,
                    "dashArray": "6 3",
                },
                highlight_function=lambda _: {
                    "fillColor": "rgba(230,57,70,0.15)",
                    "color":     "#e63946",
                    "weight":    4,
                    "fillOpacity": 0.15,
                },
                # Popup: mở sẵn, giữ nguyên khi hover — đóng khi click X
                popup=folium.Popup(
                    folium.Html(tooltip_html(sel_props), script=True),
                    max_width=320,
                    show=True,        # tự mở popup ngay khi load
                    sticky=True,      # giữ popup khi hover vào trong
                ),
                # Tooltip nhẹ khi hover (bổ sung)
                tooltip=folium.Tooltip(
                    sel_props.get("TenDVHC", ""),
                    sticky=False,
                    style="font-family:Inter,sans-serif;font-size:13px;font-weight:700;color:#e63946",
                ),
            ).add_to(m)

    return m

# ── HÀM XỬ LÝ KHÔNG DẤU ─────────────────────────────────────────
def no_accent(text: str) -> str:
    """'Phường Xuân Hòa' → 'phuong xuan hoa'"""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()

@st.cache_data
def build_ward_index(_gdf):
    names = sorted(_gdf["TenDVHC"].dropna().unique().tolist())
    names_na = [(n, no_accent(n)) for n in names]
    return names_na

_names_na = build_ward_index(gdf)

def search_wards(query: str):
    """Searchbox callback: gõ có dấu hay không dấu đều ra gợi ý tên gốc."""
    if not query or not query.strip():
        return []
    q = no_accent(query)
    return [n for n, na in _names_na if q in na]
st.markdown("""
<p class="page-title">🗺️ Trực quan hóa Dân số TP. Hồ Chí Minh</p>
<p class="page-sub">Ranh giới <b>168 phường/xã</b> — Dữ liệu địa chính HCMC</p>
""", unsafe_allow_html=True)

# ── KPI ───────────────────────────────────────────────────────────
max_name = gdf.loc[gdf["MatDo"].idxmax(), "TenDVHC"]
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-val">{gdf["DanSo"].sum():,.0f}</div>
    <div class="kpi-lbl">Tổng dân số</div>
    <div class="kpi-sub">người</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-val">{gdf["DienTich"].sum():,.1f}</div>
    <div class="kpi-lbl">Tổng diện tích</div>
    <div class="kpi-sub">km²</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-val">{gdf["MatDo"].mean():,.0f}</div>
    <div class="kpi-lbl">Mật độ trung bình</div>
    <div class="kpi-sub">người/km²</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-val">{gdf["MatDo"].max():,.0f}</div>
    <div class="kpi-lbl">Mật độ cao nhất</div>
    <div class="kpi-sub">{max_name}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────
tab_map, tab_charts, tab_rank, tab_data = st.tabs([
    "🗺️  Bản đồ", "📊  Biểu đồ", "🏆  Xếp hạng", "📋  Dữ liệu"
])

# ── TAB BẢN ĐỒ ───────────────────────────────────────────────────
with tab_map:
    col_ctrl1, col_ctrl2 = st.columns([3, 2])
    with col_ctrl1:
        metric = st.radio(
            "Tô màu theo chỉ tiêu:",
            options=["MatDo", "DanSo", "DienTich"],
            format_func=lambda x: {
                "MatDo":    "🔴  Mật độ dân số",
                "DanSo":    "🔵  Dân số",
                "DienTich": "🟢  Diện tích",
            }[x],
            horizontal=True,
        )
    with col_ctrl2:
        chosen_name = st_searchbox(
            search_wards,
            placeholder="Gõ tên phường/xã (có hoặc không dấu)…",
            label="🔍 Tìm kiếm phường/xã",
            key="ward_searchbox",
            clear_on_submit=False,
        )

    focus_name = chosen_name if chosen_name else "— Toàn TP. HCM —"

    # Thông tin phường được chọn
    if focus_name != "— Toàn TP. HCM —":
        sel_row = gdf[gdf["TenDVHC"] == focus_name]
        if not sel_row.empty:
            r = sel_row.iloc[0]
            i1, i2, i3 = st.columns(3)
            i1.info(f"👥 **Dân số:** {r['DanSo']:,.0f} người")
            i2.info(f"📐 **Diện tích:** {r['DienTich']:,.2f} km²")
            i3.info(f"🏘️ **Mật độ:** {r['MatDo']:,.0f} người/km²")

    with st.spinner("Đang tải bản đồ..."):
        fm = make_map(metric, focus_name)
        st_folium(fm, use_container_width=True, height=620,
                  returned_objects=[])   # tắt trả dữ liệu về Python — nhanh hơn

# ── TAB BIỂU ĐỒ ──────────────────────────────────────────────────
with tab_charts:
    BG = "#f8f9ff"
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Phân phối Mật độ Dân số")
        fig1 = px.histogram(
            gdf, x="MatDo", nbins=30,
            labels={"MatDo": "Mật độ (người/km²)", "count": "Số phường/xã"},
            color_discrete_sequence=["#1a56db"],
            template="plotly_white",
        )
        fig1.update_layout(paper_bgcolor=BG, plot_bgcolor=BG,
                           margin=dict(t=10, b=10), showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.markdown("#### Dân số vs Diện tích")
        fig2 = px.scatter(
            gdf, x="DienTich", y="DanSo",
            size="MatDo", color="MatDo",
            hover_name="TenDVHC",
            color_continuous_scale="YlOrRd",
            labels={"DienTich": "Diện tích (km²)", "DanSo": "Dân số", "MatDo": "Mật độ"},
            template="plotly_white",
        )
        fig2.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### Top 20 phường/xã đông dân nhất")
    top20 = gdf.nlargest(20, "DanSo")[["TenDVHC","DanSo","MatDo"]].copy()
    fig3 = px.bar(
        top20, x="TenDVHC", y="DanSo",
        color="MatDo", color_continuous_scale="OrRd",
        labels={"TenDVHC": "", "DanSo": "Dân số (người)", "MatDo": "Mật độ"},
        template="plotly_white", height=360,
    )
    fig3.update_layout(paper_bgcolor=BG, plot_bgcolor=BG,
                       xaxis_tickangle=-40, margin=dict(b=120, t=10))
    st.plotly_chart(fig3, use_container_width=True)

# ── TAB XẾP HẠNG ─────────────────────────────────────────────────
with tab_rank:
    top_n = st.slider("Hiển thị Top N", 5, 30, 15)
    r1, r2, r3 = st.columns(3)

    def hbar(col, title, cs):
        df = gdf[["TenDVHC", col]].dropna().nlargest(top_n, col)
        fig = px.bar(
            df, x=col, y="TenDVHC", orientation="h",
            color=col, color_continuous_scale=cs,
            labels={col: title, "TenDVHC": ""},
            template="plotly_white", height=420,
        )
        fig.update_layout(
            paper_bgcolor="#f8f9ff", plot_bgcolor="#f8f9ff",
            margin=dict(t=10, b=10), coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"},
        )
        return fig

    with r1:
        st.markdown(f"#### 🔵 Top {top_n} — Dân số")
        st.plotly_chart(hbar("DanSo", "Dân số (người)", "Blues"), use_container_width=True)
    with r2:
        st.markdown(f"#### 🟢 Top {top_n} — Diện tích")
        st.plotly_chart(hbar("DienTich", "Diện tích (km²)", "Greens"), use_container_width=True)
    with r3:
        st.markdown(f"#### 🔴 Top {top_n} — Mật độ")
        st.plotly_chart(hbar("MatDo", "Mật độ (người/km²)", "Oranges"), use_container_width=True)

# ── TAB DỮ LIỆU ───────────────────────────────────────────────────
with tab_data:
    df_show = gdf[["TenDVHC","DanSo","DienTich","MatDo"]].copy().reset_index(drop=True)
    df_show.columns = ["Phường/Xã","Dân số","Diện tích (km²)","Mật độ (ng/km²)"]

    s1, s2 = st.columns([2, 1])
    with s1:
        q = st.text_input("🔍 Tìm kiếm tên phường/xã", "")
    with s2:
        sort_by = st.selectbox("Sắp xếp theo", df_show.columns[1:].tolist(), index=2)

    if q:
        df_show = df_show[df_show["Phường/Xã"].str.contains(q, case=False, na=False)]
        st.caption(f"Tìm thấy **{len(df_show)}** kết quả")

    df_show = df_show.sort_values(sort_by, ascending=False).reset_index(drop=True)

    st.dataframe(
        df_show.style
            .background_gradient(
                subset=["Dân số","Diện tích (km²)","Mật độ (ng/km²)"],
                cmap="YlOrRd",
            )
            .format({
                "Dân số":           "{:,.0f}",
                "Diện tích (km²)":  "{:,.2f}",
                "Mật độ (ng/km²)":  "{:,.0f}",
            }),
        use_container_width=True,
        height=520,
    )

    st.download_button(
        "⬇️ Tải xuống CSV",
        data=df_show.to_csv(index=False).encode("utf-8-sig"),
        file_name="hcmc_danso.csv",
        mime="text/csv",
    )
