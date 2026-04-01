import streamlit as st
import csv
import io
import tempfile
import json
import os
from googleads import ad_manager

st.set_page_config(page_title="Ad Manager - Mobile Apps", page_icon="📱", layout="centered")

st.title("📱 Google Ad Manager — Add Mobile Apps")
st.markdown("Upload a CSV with one bundle ID per row to register apps in Ad Manager.")


def get_ad_manager_client():
    if "gcp_service_account" in st.secrets:
        sa = dict(st.secrets["gcp_service_account"])
        network_code = st.secrets["ad_manager"]["network_code"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sa, f)
            key_path = f.name

        yaml_content = f"""ad_manager:
  application_name: Mobile Apps Manager
  network_code: '{network_code}'
  path_to_private_key_file: {key_path}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        client = ad_manager.AdManagerClient.LoadFromStorage(path=yaml_path)
        os.unlink(yaml_path)
        return client, key_path
    else:
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "googleads.yaml")
        return ad_manager.AdManagerClient.LoadFromStorage(path=yaml_path), None


def add_apps(bundle_ids, platform, progress_bar, status_text):
    client, key_path = get_ad_manager_client()
    svc = client.GetService("MobileApplicationService", version="v202602")

    app_store = "GOOGLE_PLAY" if platform == "Android" else "APPLE_ITUNES"

    created, skipped = [], []

    for i, bundle_id in enumerate(bundle_ids):
        progress_bar.progress((i + 1) / len(bundle_ids))
        status_text.text(f"Processing {i + 1}/{len(bundle_ids)}: {bundle_id}")

        try:
            result = svc.createMobileApplications([{
                "displayName": bundle_id,
                "appStores": [app_store],
                "appStoreId": bundle_id,
            }])
            if result:
                created.append({
                    "bundle_id": bundle_id,
                    "ad_manager_id": result[0]["id"],
                    "platform": platform,
                })
        except Exception as e:
            err = str(e)
            if "NON_UNIQUE_STORE_ID" in err:
                reason = "Already exists in Ad Manager"
            elif "MISSING_APP_STORE_ENTRY" in err:
                reason = f"Not found in {'Google Play' if platform == 'Android' else 'App Store'}"
            elif "MISSING_UAM_DATA" in err:
                reason = "Missing store metadata"
            elif "MANUAL_APP_NAME_TOO_LONG" in err:
                reason = "Bundle ID too long (max 80 chars)"
            elif "PUBLISHER_HAS_TOO_MANY_ACTIVE_APPS" in err:
                reason = "Account app limit reached"
            else:
                reason = err[:120]
            skipped.append({
                "bundle_id": bundle_id,
                "platform": platform,
                "reason": reason,
            })

    if key_path:
        os.unlink(key_path)

    return created, skipped


# --- Instructions ---
with st.expander("How to use"):
    st.markdown("""
1. Select the platform (Android or iOS)
2. Upload a CSV file with **one bundle ID per row** — no header needed

**Example CSV for Android:**
```
com.example.app
com.another.game
com.mygame.puzzle
```

**Example CSV for iOS:**
```
com.example.iosapp
com.another.iosgame
```
""")
    col1, col2 = st.columns(2)
    with col1:
        sample_android = "com.example.app\ncom.another.game\ncom.mygame.puzzle\n"
        st.download_button("Download Android sample", sample_android, file_name="android_apps.csv", mime="text/csv")
    with col2:
        sample_ios = "com.example.iosapp\ncom.another.iosgame\n"
        st.download_button("Download iOS sample", sample_ios, file_name="ios_apps.csv", mime="text/csv")

# --- Platform selector ---
platform = st.radio("Platform", ["Android", "iOS"], horizontal=True)

# --- File upload ---
uploaded_file = st.file_uploader("Upload CSV with bundle IDs", type="csv")

if uploaded_file:
    content = uploaded_file.read().decode("utf-8").strip()

    # Parse: support both plain list and single-column CSV with or without header
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Strip surrounding quotes if present
    lines = [l.strip('"').strip("'") for l in lines]

    # Drop header row if it looks like a label (no dots = not a bundle ID)
    if lines and "." not in lines[0]:
        lines = lines[1:]

    # Remove any extra columns if user uploaded multi-column CSV
    bundle_ids = [l.split(",")[0].strip().strip('"') for l in lines if l]
    bundle_ids = [b for b in bundle_ids if b]

    if not bundle_ids:
        st.error("No bundle IDs found in the file.")
    else:
        st.success(f"Loaded **{len(bundle_ids)} bundle IDs** for **{platform}**")

        with st.expander("Preview bundle IDs"):
            st.code("\n".join(bundle_ids[:20]) + ("\n..." if len(bundle_ids) > 20 else ""))

        if st.button("Add to Ad Manager", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            created, skipped = add_apps(bundle_ids, platform, progress_bar, status_text)

            status_text.empty()
            progress_bar.progress(1.0)

            # --- Summary ---
            total = len(bundle_ids)
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", total)
            col2.metric("Created", len(created), delta=f"+{len(created)}")
            col3.metric("Skipped", len(skipped))

            # --- Created ---
            if created:
                st.markdown("### ✅ Successfully Created")
                st.dataframe(created, use_container_width=True)
                created_csv = "bundle_id,platform,ad_manager_id\n" + \
                    "\n".join(f"{r['bundle_id']},{r['platform']},{r['ad_manager_id']}" for r in created)
                st.download_button("Download created apps", created_csv, file_name="created_apps.csv", mime="text/csv")

            # --- Skipped ---
            if skipped:
                st.markdown("### ⚠️ Skipped / Errors")
                st.dataframe(skipped, use_container_width=True)

                # Group errors by reason for summary
                from collections import Counter
                reasons = Counter(r["reason"] for r in skipped)
                st.markdown("**Error summary:**")
                for reason, count in reasons.most_common():
                    st.markdown(f"- **{reason}** — {count} app(s)")

                skipped_csv = "bundle_id,platform,reason\n" + \
                    "\n".join(f"{r['bundle_id']},{r['platform']},{r['reason']}" for r in skipped)
                st.download_button("Download skipped apps", skipped_csv, file_name="skipped_apps.csv", mime="text/csv")
