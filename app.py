import streamlit as st
import csv
import io
import tempfile
import json
import os
from googleads import ad_manager

st.set_page_config(page_title="Ad Manager - Mobile Apps", page_icon="📱", layout="centered")

st.title("📱 Google Ad Manager — Add Mobile Apps")
st.markdown("Upload a CSV with your app bundle IDs to register them in Ad Manager.")


def get_ad_manager_client():
    """Initialize Ad Manager client from Streamlit secrets or local yaml."""
    if "gcp_service_account" in st.secrets:
        # Running on Streamlit Cloud — write secrets to a temp file
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
        # Local dev — use googleads.yaml in project directory
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "googleads.yaml")
        return ad_manager.AdManagerClient.LoadFromStorage(path=yaml_path), None


def add_apps(apps_data, progress_bar, status_text):
    client, key_path = get_ad_manager_client()
    svc = client.GetService("MobileApplicationService", version="v202602")

    created, skipped = [], []

    for i, app in enumerate(apps_data):
        progress_bar.progress((i + 1) / len(apps_data))
        status_text.text(f"Processing {i + 1}/{len(apps_data)}: {app['app_store_id']}")

        try:
            result = svc.createMobileApplications([{
                "displayName": app["display_name"],
                "appStores": [app["app_store"]],
                "appStoreId": app["app_store_id"],
            }])
            if result:
                created.append({
                    "display_name": app["display_name"],
                    "app_store": app["app_store"],
                    "app_store_id": app["app_store_id"],
                    "id": result[0]["id"],
                })
        except Exception as e:
            err = str(e)
            if "NON_UNIQUE_STORE_ID" in err:
                reason = "Already exists"
            elif "MISSING_APP_STORE_ENTRY" in err:
                reason = "Not found in store"
            elif "MISSING_UAM_DATA" in err:
                reason = "Missing store data"
            elif "MANUAL_APP_NAME_TOO_LONG" in err:
                reason = "Display name too long"
            else:
                reason = err[:100]
            skipped.append({
                "display_name": app["display_name"],
                "app_store": app["app_store"],
                "app_store_id": app["app_store_id"],
                "reason": reason,
            })

    if key_path:
        os.unlink(key_path)

    return created, skipped


# --- CSV format instructions ---
with st.expander("CSV format"):
    st.markdown("""
Your CSV must have these columns:

| display_name | app_store | app_store_id |
|---|---|---|
| My Android App | GOOGLE_PLAY | com.example.app |
| My iOS App | APPLE_ITUNES | com.example.iosapp |

**`app_store` values:** `GOOGLE_PLAY` or `APPLE_ITUNES`

**`app_store_id`:**
- Android → package name (e.g. `com.example.app`)
- iOS → bundle ID (e.g. `com.example.app`)
""")
    sample = "display_name,app_store,app_store_id\nMy Android App,GOOGLE_PLAY,com.example.app\nMy iOS App,APPLE_ITUNES,com.example.iosapp\n"
    st.download_button("Download sample CSV", sample, file_name="sample_apps.csv", mime="text/csv")

# --- File upload ---
uploaded_file = st.file_uploader("Upload your CSV", type="csv")

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    apps = []
    errors = []
    for i, row in enumerate(reader, start=2):
        missing = [c for c in ["display_name", "app_store", "app_store_id"] if c not in row or not row[c].strip()]
        if missing:
            errors.append(f"Row {i}: missing columns {missing}")
            continue
        if row["app_store"].strip() not in ("GOOGLE_PLAY", "APPLE_ITUNES"):
            errors.append(f"Row {i}: invalid app_store value '{row['app_store']}' (must be GOOGLE_PLAY or APPLE_ITUNES)")
            continue
        apps.append({
            "display_name": row["display_name"].strip(),
            "app_store": row["app_store"].strip(),
            "app_store_id": row["app_store_id"].strip(),
        })

    if errors:
        st.error("CSV has errors:\n" + "\n".join(errors))
    else:
        android = sum(1 for a in apps if a["app_store"] == "GOOGLE_PLAY")
        ios = sum(1 for a in apps if a["app_store"] == "APPLE_ITUNES")
        st.success(f"Loaded **{len(apps)} apps** — {android} Android, {ios} iOS")

        if st.button("Add to Ad Manager", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            with st.spinner("Adding apps..."):
                created, skipped = add_apps(apps, progress_bar, status_text)

            status_text.empty()
            progress_bar.progress(1.0)

            st.markdown(f"### Results: {len(created)} created, {len(skipped)} skipped")

            if created:
                st.markdown("#### ✅ Created")
                st.dataframe(
                    created,
                    column_order=["display_name", "app_store", "app_store_id", "id"],
                    use_container_width=True,
                )
                created_csv = "display_name,app_store,app_store_id,ad_manager_id\n" + \
                    "\n".join(f"{r['display_name']},{r['app_store']},{r['app_store_id']},{r['id']}" for r in created)
                st.download_button("Download created apps CSV", created_csv, file_name="created_apps.csv", mime="text/csv")

            if skipped:
                st.markdown("#### ⚠️ Skipped")
                st.dataframe(
                    skipped,
                    column_order=["display_name", "app_store", "app_store_id", "reason"],
                    use_container_width=True,
                )
