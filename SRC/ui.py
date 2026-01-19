# src/ui.py
import streamlit as st
import json
from pathlib import Path

from .viewer import (
    get_scrolls,
    fetch_manifest,
    reconstruct,
)


def main():
    st.set_page_config(
        page_title="Ledger Scrolls Viewer",
        page_icon="📜",
        layout="wide",
    )

    st.title("Ledger Scrolls 📜")
    st.caption("Permissionless, immutable documents on Cardano")

    # Sidebar controls
    with st.sidebar:
        st.header("Settings")

        use_registry = st.checkbox("Use on-chain registry", value=True)
        use_blockfrost = st.checkbox("Use Blockfrost for metadata (faster)", value=False)

        blockfrost_key = None
        if use_blockfrost:
            blockfrost_key = st.text_input(
                "Blockfrost Project ID",
                type="password",
                help="Required when using Blockfrost mode",
            )

        custom_registry_file = st.file_uploader(
            "Optional: custom registry JSON",
            type=["json"],
            help="Upload your own registry datum content (uncompressed)",
        )

    # Main area
    try:
        if custom_registry_file is not None:
            custom_data = json.load(custom_registry_file)
            scrolls = custom_data.get("scrolls", [])
            st.info("Using custom uploaded registry")
        else:
            scrolls = get_scrolls(use_registry=use_registry)

        if not scrolls:
            st.warning("No scrolls found in registry. Falling back to demo entries.")
            scrolls = get_scrolls(use_registry=False)

        scroll_titles = [s.get("title", f"Untitled ({s.get('id')})") for s in scrolls]
        selected_title = st.selectbox("Select document to view", scroll_titles)

        if selected_title:
            scroll = next(s for s in scrolls if s.get("title") == selected_title)

            st.subheader(scroll.get("title", "Unnamed Scroll"))

            if st.button("Reconstruct document", type="primary"):
                with st.spinner("Fetching manifest & reconstructing..."):
                    try:
                        manifest = fetch_manifest(
                            scroll,
                            use_blockfrost=use_blockfrost,
                            bf_key=blockfrost_key,
                        )

                        data, content_type = reconstruct(scroll, manifest)

                        ext = "html" if "html" in content_type.lower() else "txt"
                        filename = f"{selected_title.replace(' ', '_')}.{ext}"

                        st.success("Document reconstructed successfully!")

                        # Preview for text/html
                        if "html" in content_type.lower():
                            st.markdown(data.decode("utf-8", errors="replace"), unsafe_allow_html=True)
                        else:
                            st.text_area("Content preview (first 2000 chars)", data.decode("utf-8", errors="replace")[:2000])

                        # Download button
                        st.download_button(
                            label="Download document",
                            data=data,
                            file_name=filename,
                            mime=content_type,
                        )

                    except Exception as e:
                        st.error(f"Reconstruction failed\n\n{str(e)}")

    except Exception as e:
        st.error(f"Could not load scrolls / registry\n\n{str(e)}")


if __name__ == "__main__":
    main()
