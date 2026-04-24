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

DEFAULT_APP_URL = "https://rfidmockup-j5ej5tiat2vkzhsxsjccka.streamlit.app"

def get_base_url():
    if st.session_state.get("base_url"):
        return st.session_state["base_url"].rstrip("/")
    try:
        url = st.secrets.get("base_url", "")
        if url:
            return url.rstrip("/")
    except:
        pass
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

# ─────────────────────────────────────────────
# SHARED EDIT FORM (used by viewer page)
# ─────────────────────────────────────────────
def _show_edit_form(bin_id, rec, data, is_empty=False):
    st.markdown(f"""
    <div style="background:#0f2240;border:1px solid #2a4a7a;border-radius:10px;
        padding:1rem 1.25rem;margin-bottom:1rem;">
      <div style="font-size:1rem;font-weight:700;color:#4f9cf9;">
          ✎  {'Register Material' if is_empty else 'Edit Material'} — Bin {bin_id}</div>
      <div style="font-size:0.85rem;color:#7a8299;margin-top:4px;">
          Select from known values or choose "type custom value" to enter new data.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(key=f"viewer_form_{bin_id}"):
        new_vals = {}
        for field in EXPECTED_COLS:
            current_val = rec.get(field, "")
            if field in DROPDOWN_FIELDS:
                options = get_field_options(data, field)
                CUSTOM = "— type custom value —"
                choices = options + [CUSTOM]
                default_idx = options.index(current_val) if current_val in options else len(choices) - 1
                selected = st.selectbox(field, options=choices, index=default_idx,
                                        key=f"vf_sel_{bin_id}_{field}")
                if selected == CUSTOM:
                    new_vals[field] = st.text_input(
                        f"Custom {field}",
                        value=current_val if current_val not in options else "",
                        key=f"vf_custom_{bin_id}_{field}",
                        placeholder=f"Enter {field}...")
                else:
                    new_vals[field] = selected
            else:
                new_vals[field] = st.text_input(
                    field, value=current_val, key=f"vf_inp_{bin_id}_{field}")

        st.markdown("---")
        confirmed = st.checkbox(
            "✅  I confirm the information above is correct and ready to save.",
            key=f"vf_confirm_{bin_id}"
        )
        cs, cc = st.columns(2)
        with cs:
            submitted = st.form_submit_button(
                "💾  Save Material", type="primary",
                use_container_width=True, disabled=not confirmed)
        with cc:
            cancelled = st.form_submit_button("✕  Cancel", use_container_width=True)

        if submitted and confirmed:
            new_vals["_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data[bin_id] = new_vals
            save_data(data)
            st.session_state.pop(f"v_mode_{bin_id}", None)
            st.success(f"✅ Bin {bin_id} saved successfully!")
            st.rerun()
        if cancelled:
            st.session_state.pop(f"v_mode_{bin_id}", None)
            st.rerun()

# ─────────────────────────────────────────────
# VIEWER MODE — shown when ?bin=XXXXX in URL
# ─────────────────────────────────────────────
def show_viewer(bin_id):
    data = load_data()

    st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 0 !important; padding-bottom: 2rem;}
    .stButton > button {font-size: 1rem !important; padding: 0.6rem 1rem !important;}
    div[data-testid="stForm"] {border: none; padding: 0;}
    </style>
    """, unsafe_allow_html=True)

    # Header bar
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0a1628,#15103a);
        padding:1.4rem 1.5rem 1.2rem;margin-bottom:1.2rem;
        border-bottom:3px solid #4f9cf9;">
      <div style="font-family:monospace;color:#4f9cf9;font-size:0.8rem;
          letter-spacing:3px;margin-bottom:6px;">📦 RFID · QR SYSTEM</div>
      <div style="font-size:0.85rem;color:#7a8299;letter-spacing:1px;">STORAGE BIN</div>
      <div style="font-size:2.8rem;font-weight:800;color:#ffffff;
          letter-spacing:2px;line-height:1.1;margin-top:2px;">{bin_id}</div>
    </div>
    """, unsafe_allow_html=True)

    # Bin not found
    if bin_id not in data:
        st.markdown("""
        <div style="background:#1a1d27;border:2px solid #f87171;border-radius:12px;
            padding:2rem;text-align:center;margin-top:1rem;">
          <div style="font-size:3rem;margin-bottom:0.5rem;">❌</div>
          <div style="font-size:1.2rem;font-weight:700;color:#f87171;">Bin Not Registered</div>
          <div style="color:#7a8299;margin-top:0.5rem;font-size:0.95rem;">
              Contact your warehouse administrator.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    rec = data[bin_id]

    # Cleared / empty bin
    if rec.get("_cleared"):
        st.markdown(f"""
        <div style="background:#1a1d27;border:2px solid #fbbf24;border-radius:12px;
            padding:2rem;text-align:center;margin-bottom:1.5rem;">
          <div style="font-size:3rem;margin-bottom:0.5rem;">📭</div>
          <div style="font-size:1.3rem;font-weight:700;color:#fbbf24;">Bin is Empty</div>
          <div style="color:#7a8299;margin-top:0.5rem;font-size:0.9rem;">
              No material registered · Cleared: {rec.get("_cleared_at","unknown")}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Register new material into this bin")
        _show_edit_form(bin_id, rec, data, is_empty=True)
        return

    # Material hero card
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f2a52,#1a1040);
        border:1px solid #3a5a9a;border-radius:14px;
        padding:1.4rem 1.5rem;margin-bottom:1.2rem;">
      <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:2px;
          color:#7a8299;margin-bottom:6px;">Material ID</div>
      <div style="font-family:monospace;font-size:2rem;font-weight:800;
          color:#4f9cf9;letter-spacing:2px;line-height:1.1;">
          {rec.get("Material","—")}</div>
      <div style="font-size:1.25rem;font-weight:600;color:#e8ecf4;
          margin-top:8px;line-height:1.3;">
          {rec.get("Material Description","—")}</div>
    </div>
    """, unsafe_allow_html=True)

    # Info table
    def info_row(icon, label, value, highlight=False):
        val_color = "#34d399" if highlight else "#e8ecf4"
        val_size  = "1.15rem" if highlight else "1rem"
        return f"""
        <div style="display:flex;align-items:center;padding:0.85rem 1rem;
            border-bottom:1px solid #1e2336;gap:0.75rem;">
          <div style="font-size:1.3rem;width:32px;text-align:center;flex-shrink:0;">{icon}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;
                color:#5a6280;margin-bottom:2px;">{label}</div>
            <div style="font-size:{val_size};font-weight:600;color:{val_color};
                word-break:break-word;">{value or "—"}</div>
          </div>
        </div>"""

    stock_val = f"{rec.get('Total Stock','')} {rec.get('Base Unit of Measure','')}".strip()

    rows_html = "".join([
        info_row("🏭", "Plant",            rec.get("Plant","")),
        info_row("📍", "Storage Location", rec.get("Storage Location","")),
        info_row("🗂", "Storage Type",     rec.get("Storage Type","")),
        info_row("📂", "Storage Section",  rec.get("Storage Section","")),
        info_row("📦", "Storage Bin",      rec.get("Storage Bin","")),
        info_row("🏷", "Batch",            rec.get("Batch","")),
        info_row("📋", "Stock Category",   rec.get("Stock Category","")),
        info_row("📊", "Total Stock",      stock_val, highlight=True),
        info_row("📅", "SLED / BBD",       rec.get("SLED/BBD","")),
        info_row("📅", "GR Date",          rec.get("GR Date","")),
    ])

    st.markdown(f"""
    <div style="background:#13162a;border:1px solid #2e3347;border-radius:14px;
        overflow:hidden;margin-bottom:1.2rem;">
      <div style="background:#1a1d35;padding:0.75rem 1rem;border-bottom:1px solid #2e3347;">
        <span style="font-size:0.72rem;text-transform:uppercase;letter-spacing:2px;
            color:#5a6280;font-weight:600;">Material Details</span>
      </div>
      {rows_html}
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"🕐 Last updated: {rec.get('_updated_at','unknown')}  ·  Scan again to refresh")

    # Action buttons
    st.markdown("---")
    st.markdown("#### Warehouse Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✎  Edit Material", use_container_width=True, type="primary",
                     key=f"v_edit_{bin_id}"):
            st.session_state[f"v_mode_{bin_id}"] = "edit"
            st.rerun()
    with col2:
        if st.button("🗑  Clear Bin", use_container_width=True,
                     key=f"v_clear_btn_{bin_id}"):
            st.session_state[f"v_mode_{bin_id}"] = "confirm_clear"
            st.rerun()

    mode = st.session_state.get(f"v_mode_{bin_id}", "")

    # Confirm clear dialog
    if mode == "confirm_clear":
        st.markdown(f"""
        <div style="background:#2a1010;border:2px solid #f87171;border-radius:12px;
            padding:1.25rem 1.5rem;margin-top:1rem;">
          <div style="font-size:1.1rem;font-weight:700;color:#f87171;margin-bottom:0.5rem;">
              ⚠️  Confirm Clear Bin</div>
          <div style="color:#e8ecf4;font-size:0.95rem;line-height:1.6;">
              This will remove all material data from bin <strong>{bin_id}</strong>.<br>
              The QR code will remain unchanged.<br><br>
              <strong>Are you sure?</strong>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(" ")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✅  Yes, Clear Bin", use_container_width=True, type="primary",
                         key=f"v_confirm_clear_{bin_id}"):
                data[bin_id] = {
                    "Storage Bin": bin_id,
                    "_cleared": True,
                    "_cleared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_data(data)
                st.session_state.pop(f"v_mode_{bin_id}", None)
                st.success("✅ Bin cleared successfully.")
                st.rerun()
        with cc2:
            if st.button("✕
