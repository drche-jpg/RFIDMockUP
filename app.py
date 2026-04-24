import streamlit as st
import pandas as pd
import json
import qrcode
import io
import os
import zipfile
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import base64

st.set_page_config(
    page_title="RFID·QR Material Manager",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DATA_FILE = "material_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────
# URL HELPER
# ─────────────────────────────────────────────
DEFAULT_APP_URL = "https://rfidmockup-j5ej5tiat2vkzhsxsjccka.streamlit.app"

def get_base_url():
    # 1. User changed it this session
    if st.session_state.get("base_url"):
        return st.session_state["base_url"].rstrip("/")
    # 2. Streamlit secrets override
    try:
        url = st.secrets.get("base_url", "")
        if url:
            return url.rstrip("/")
    except:
        pass
    # 3. Hardcoded default
    return DEFAULT_APP_URL

def bin_url(storage_bin):
    return f"{get_base_url()}?bin={storage_bin}"

def make_qr_image(url, bin_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    label_h = 50
    canvas = Image.new("RGB", (qr_img.width, qr_img.height + label_h), "white")
    canvas.paste(qr_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        font_big = ImageFont.load_default()
        font_sm  = font_big
    bbox = draw.textbbox((0, 0), bin_id, font=font_big)
    tw = bbox[2] - bbox[0]
    draw.text(((qr_img.width - tw) // 2, qr_img.height + 6), bin_id, fill="black", font=font_big)
    sub = "Scan for material info"
    bbox2 = draw.textbbox((0, 0), sub, font=font_sm)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((qr_img.width - tw2) // 2, qr_img.height + 28), sub, fill="#666666", font=font_sm)
    return canvas

def qr_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

EXPECTED_COLS = [
    "Material", "Plant", "Storage Location", "Storage Type",
    "Storage Section", "Storage Bin", "Material Description",
    "Batch", "Stock Category", "Total Stock",
    "Base Unit of Measure", "SLED/BBD", "GR Date"
]

DROPDOWN_FIELDS = [
    "Material", "Plant", "Storage Location", "Storage Type",
    "Storage Section", "Stock Category", "Base Unit of Measure"
]

FREETEXT_FIELDS = [
    "Storage Bin", "Material Description", "Batch",
    "Total Stock", "SLED/BBD", "GR Date"
]

def get_field_options(data, field):
    vals = set()
    for rec in data.values():
        v = rec.get(field, "").strip()
        if v and not v.startswith("_"):
            vals.add(v)
    return sorted(vals)

def parse_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, dtype=str).fillna("")
        df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
        return df, None
    except Exception as e:
        return None, str(e)

def show_viewer(bin_id):
    data = load_data()
    st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1b3e,#1a1040);
        padding:1.2rem 1.5rem;border-radius:10px;margin-bottom:1.2rem;">
      <div style="font-family:monospace;color:#4f9cf9;font-size:0.85rem;letter-spacing:2px;">RFID·QR SYSTEM</div>
      <div style="font-size:1.6rem;font-weight:700;color:#fff;margin-top:4px;">Bin: {bin_id}</div>
      <div style="font-size:0.72rem;color:#7a8299;margin-top:2px;">Storage Bin Material Information</div>
    </div>
    """, unsafe_allow_html=True)

    if bin_id not in data:
        st.error(f"No data registered for bin **{bin_id}**")
        st.info("This bin has not been registered yet.")
        return

    rec = data[bin_id]

    if rec.get("_cleared"):
        st.warning("This bin is currently **empty**. No material is registered.")
        st.caption(f"Cleared at: {rec.get('_cleared_at', 'unknown')}")
        return

    st.markdown(f"""
    <div style="background:#1a1d27;border:1px solid #2e3347;border-radius:10px;
        padding:1rem 1.25rem;margin-bottom:1rem;">
      <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;
          color:#7a8299;margin-bottom:4px;">Material</div>
      <div style="font-size:1.1rem;font-weight:700;color:#e8ecf4;">
          {rec.get('Material Description', '—')}</div>
      <div style="font-family:monospace;font-size:0.78rem;color:#4f9cf9;margin-top:2px;">
          {rec.get('Material', '—')}</div>
    </div>
    """, unsafe_allow_html=True)

    fields = [
        ("Plant",            rec.get("Plant", "")),
        ("Storage Location", rec.get("Storage Location", "")),
        ("Storage Type",     rec.get("Storage Type", "")),
        ("Storage Section",  rec.get("Storage Section", "")),
        ("Storage Bin",      rec.get("Storage Bin", "")),
        ("Batch",            rec.get("Batch", "")),
        ("Stock Category",   rec.get("Stock Category", "")),
        ("Total Stock",      f"{rec.get('Total Stock', '')} {rec.get('Base Unit of Measure', '')}"),
        ("SLED / BBD",       rec.get("SLED/BBD", "")),
        ("GR Date",          rec.get("GR Date", "")),
    ]

    for label, value in fields:
        col1, col2 = st.columns([2, 3])
        with col1:
            st.markdown(f"<span style='color:#7a8299;font-size:0.8rem;'>{label}</span>",
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f"<span style='font-weight:500;font-size:0.85rem;'>{value or '—'}</span>",
                        unsafe_allow_html=True)
        st.divider()

    st.caption(f"Last updated: {rec.get('_updated_at', 'unknown')} · Scan again to refresh")

ADMIN_CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
.stTabs [data-baseweb="tab-list"] {gap: 8px;}
.stTabs [data-baseweb="tab"] {padding: 6px 20px; border-radius: 6px; font-size: 0.82rem;}
.stTabs [aria-selected="true"] {background: #1a3a6b !important; color: #4f9cf9 !important;}
</style>
"""

def tab_setup():
    st.subheader("App Configuration")

    st.markdown("### App URL (for QR codes)")
    st.success(f"**Active URL:** {get_base_url()}")
    st.caption("This URL is already set and embedded in every QR code.")

    with st.expander("Change URL (optional)"):
        st.warning("Only change this if you move the app to a different address.")
        url_input = st.text_input(
            "New App URL",
            value=get_base_url(),
            placeholder="https://your-app-name.streamlit.app",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save new URL", type="primary", use_container_width=True):
                st.session_state["base_url"] = url_input.strip().rstrip("/")
                st.success(f"URL updated to: {url_input.strip()}")
                st.rerun()
        with col2:
            if st.button("Reset to default", use_container_width=True):
                st.session_state.pop("base_url", None)
                st.success(f"Reset to: {DEFAULT_APP_URL}")
                st.rerun()

    st.markdown("---")
    st.markdown("### How it works")
    st.info("""
- Material data is stored in a JSON file on the Streamlit server
- QR codes link to this app with ?bin=STORAGE_BIN added to the URL
- Any phone that scans the QR opens the material info page instantly
- The QR code URL never changes — only the data behind it changes
""")

    st.markdown("---")
    st.markdown("### Database status")
    data = load_data()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total bins", len(data))
    col2.metric("Active bins", sum(1 for v in data.values()
                                   if not v.get("_cleared") and v.get("Material")))
    col3.metric("Empty bins", sum(1 for v in data.values()
                                   if v.get("_cleared") or not v.get("Material")))
    if data:
        st.markdown("---")
        if st.button("Reset ALL data", type="secondary"):
            save_data({})
            st.success("All data cleared.")
            st.rerun()

def tab_register():
    st.subheader("📋 Import Materials from CSV")
    uploaded = st.file_uploader("Upload your CSV file", type=["csv"])

    if not uploaded:
        st.markdown("""
**Expected columns:**
Material · Plant · Storage Location · Storage Type · Storage Section ·
Storage Bin · Material Description · Batch · Stock Category ·
Total Stock · Base Unit of Measure · SLED/BBD · GR Date
""")
        return

    df, err = parse_csv(uploaded)
    if err:
        st.error(f"CSV parse error: {err}")
        return

    st.success(f"Loaded {len(df)} rows")
    st.dataframe(df, use_container_width=True, height=250)
    st.markdown("---")
    overwrite = st.checkbox("Overwrite existing bins", value=True)

    if st.button("☁ Register All to Database", type="primary", use_container_width=True):
        data = load_data()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        skipped = 0
        registered = 0
        prog = st.progress(0, text="Registering...")
        for i, row in df.iterrows():
            bin_id = str(row.get("Storage Bin", "")).strip()
            if not bin_id:
                skipped += 1
                continue
            if bin_id in data and not overwrite:
                skipped += 1
                continue
            rec = {col: str(row.get(col, "")).strip() for col in EXPECTED_COLS}
            rec["_updated_at"] = now
            data[bin_id] = rec
            registered += 1
            prog.progress((i + 1) / len(df), text=f"Registering {bin_id}...")
        save_data(data)
        prog.empty()
        st.success(f"{registered} bins registered · {skipped} skipped")
        st.balloons()

def tab_qrcodes():
    st.subheader("◻ QR Code Gallery")
    data = load_data()

    if not data:
        st.warning("No bins registered yet. Go to the Register tab first.")
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        search = st.text_input("Search bins", placeholder="Filter by bin ID or material...",
                               label_visibility="collapsed")
    with col2:
        dl_all = st.button("⬇ Download All", use_container_width=True)

    bins = {k: v for k, v in data.items()
            if search.lower() in k.lower()
            or search.lower() in v.get("Material", "").lower()
            or search.lower() in v.get("Material Description", "").lower()}

    st.caption(f"Showing {len(bins)} of {len(data)} bins")

    if dl_all:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for bid in data:
                img = make_qr_image(bin_url(bid), bid)
                zf.writestr(f"QR_{bid}.png", qr_to_bytes(img))
        zip_buf.seek(0)
        st.download_button("📦 Click here to download ZIP", data=zip_buf,
                           file_name="RFID_QR_Codes.zip", mime="application/zip")

    cols = st.columns(4)
    for i, (bid, rec) in enumerate(bins.items()):
        img = make_qr_image(bin_url(bid), bid)
        has_data = bool(rec.get("Material")) and not rec.get("_cleared")
        with cols[i % 4]:
            st.image(img, caption=bid, use_container_width=True)
            st.caption("● Active" if has_data else "○ Empty")
            st.download_button(
                "⬇ PNG", data=qr_to_bytes(img),
                file_name=f"QR_{bid}.png", mime="image/png",
                key=f"dl_{bid}", use_container_width=True
            )

def tab_manage():
    st.subheader("🗂 Material Bin Manager")
    data = load_data()

    if not data:
        st.warning("No bins registered yet.")
        return

    search = st.text_input("Search", placeholder="Filter by bin, material, description...",
                           label_visibility="collapsed")

    bins = {k: v for k, v in data.items()
            if search.lower() in k.lower()
            or search.lower() in v.get("Material", "").lower()
            or search.lower() in v.get("Material Description", "").lower()}

    st.caption(f"{len(bins)} bins shown")

    for bin_id, rec in bins.items():
        has_data = bool(rec.get("Material")) and not rec.get("_cleared")
        icon = "●" if has_data else "○"
        desc = rec.get("Material Description", "(empty)")[:60]

        with st.expander(f"{icon} **{bin_id}** — {desc}"):

            col1, col2 = st.columns([3, 1])
            with col1:
                if has_data:
                    st.markdown(f"**Material:** `{rec.get('Material', '—')}`")
                    st.markdown(f"**Stock:** {rec.get('Total Stock', '—')} "
                                f"{rec.get('Base Unit of Measure', '')}")
                    st.markdown(f"**Batch:** {rec.get('Batch', '—')}")
                    st.markdown(f"**GR Date:** {rec.get('GR Date', '—')}")
                    st.markdown(f"**SLED/BBD:** {rec.get('SLED/BBD', '—')}")
                else:
                    st.info("Bin is empty — ready for new material")
            with col2:
                st.markdown(f"[🔗 View page]({bin_url(bin_id)})")

            st.markdown("---")
            c1, c2, c3 = st.columns(3)

            with c1:
                if st.button("✎ Edit / Register", key=f"edit_{bin_id}",
                             use_container_width=True, type="primary"):
                    st.session_state[f"editing_{bin_id}"] = True

            with c2:
                if st.button("✕ Clear bin", key=f"clear_{bin_id}",
                             use_container_width=True):
                    data[bin_id] = {
                        "Storage Bin": bin_id,
                        "_cleared": True,
                        "_cleared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_data(data)
                    st.session_state[f"editing_{bin_id}"] = False
                    st.success(f"Bin {bin_id} cleared. QR code unchanged.")
                    st.rerun()

            with c3:
                qr_img = make_qr_image(bin_url(bin_id), bin_id)
                st.download_button(
                    "⬇ QR PNG", data=qr_to_bytes(qr_img),
                    file_name=f"QR_{bin_id}.png", mime="image/png",
                    key=f"qrdl_{bin_id}", use_container_width=True
                )

            if st.session_state.get(f"editing_{bin_id}"):
                st.markdown("---")
                st.markdown("#### ✎ Edit / Register material")
                st.caption(
                    "Dropdown fields show all known values from your data. "
                    "Choose from the list or select **— type custom value —** "
                    "to enter something new."
                )

                with st.form(key=f"form_{bin_id}"):
                    new_vals = {}
                    col_a, col_b = st.columns(2)

                    for j, field in enumerate(EXPECTED_COLS):
                        target = col_a if j % 2 == 0 else col_b
                        current_val = rec.get(field, "")

                        with target:
                            if field in DROPDOWN_FIELDS:
                                options = get_field_options(data, field)
                                CUSTOM = "— type custom value —"
                                choices = options + [CUSTOM]

                                if current_val in options:
                                    default_idx = options.index(current_val)
                                else:
                                    default_idx = len(choices) - 1

                                selected = st.selectbox(
                                    field,
                                    options=choices,
                                    index=default_idx,
                                    key=f"sel_{bin_id}_{field}"
                                )

                                if selected == CUSTOM:
                                    new_vals[field] = st.text_input(
                                        f"Custom {field}",
                                        value=current_val if current_val not in options else "",
                                        key=f"custom_{bin_id}_{field}",
                                        placeholder=f"Enter {field}..."
                                    )
                                else:
                                    new_vals[field] = selected

                            else:
                                new_vals[field] = st.text_input(
                                    field,
                                    value=current_val,
                                    key=f"inp_{bin_id}_{field}"
                                )

                    st.markdown(" ")
                    c_save, c_cancel = st.columns(2)
                    with c_save:
                        submitted = st.form_submit_button(
                            "💾 Save Changes", type="primary", use_container_width=True)
                    with c_cancel:
                        cancelled = st.form_submit_button(
                            "✕ Cancel", use_container_width=True)

                    if submitted:
                        new_vals["_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        data[bin_id] = new_vals
                        save_data(data)
                        st.session_state[f"editing_{bin_id}"] = False
                        st.success(f"✅ Bin {bin_id} updated!")
                        st.rerun()

                    if cancelled:
                        st.session_state[f"editing_{bin_id}"] = False
                        st.rerun()

def main():
    params = st.query_params
    bin_param = params.get("bin", None)

    if bin_param:
        show_viewer(bin_param)
        return

    st.markdown(ADMIN_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1b3e,#1a1040);
        padding:1rem 1.5rem;border-radius:10px;margin-bottom:1rem;">
      <div style="font-family:monospace;color:#4f9cf9;font-size:1rem;
          letter-spacing:2px;font-weight:700;">
          RFID·QR MANAGER</div>
      <div style="font-size:0.72rem;color:#7a8299;margin-top:2px;">
          MATERIAL TRACKING SYSTEM</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["⚙ Setup", "📋 Register", "◻ QR Codes", "🗂 Manage"])
    with tab1: tab_setup()
    with tab2: tab_register()
    with tab3: tab_qrcodes()
    with tab4: tab_manage()

if __name__ == "__main__":
    main()
