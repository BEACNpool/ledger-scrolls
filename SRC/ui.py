import streamlit as st
import json
from pathlib import Path

from .viewer import (
    get_scrolls,
    fetch_manifest,
    reconstruct,
    DEFAULT_SCROLLS,
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

        use_blockfrost = st.checkbox("Use Blockfrost for metadata (faster & recommended)", value=True)

        blockfrost_key = None
        if use_blockfrost:
            blockfrost_key = st.text_input(
                "Blockfrost Project ID / API Key",
                type="password",
                help="Required for Blockfrost mode (get from blockfrost.io)",
                key="bf_key_input",
            )

        custom_registry_file = st.file_uploader(
            "Optional: custom registry JSON (uncompressed datum content)",
            type=["json"],
            help="Upload a JSON file with the registry structure",
        )

        if use_blockfrost and not blockfrost_key:
            st.warning("Blockfrost API key is required when using Blockfrost mode.")

    # Main area
    try:
        # Load scrolls
        if custom_registry_file is not None:
            custom_data = json.load(custom_registry_file)
            scrolls = custom_data.get("scrolls", [])
            st.info("Using custom uploaded registry JSON")
        else:
            scrolls = get_scrolls(use_registry=use_registry)

        if not scrolls:
            st.warning("No scrolls found in registry. Falling back to built-in demo entries.")
            scrolls = DEFAULT_SCROLLS.copy()

        # Display available scrolls
        scroll_titles = [s.get("title", f"Untitled ({s.get('id', '-')})") for s in scrolls]
        selected_title = st.selectbox("Select document to view", scroll_titles)

        if selected_title:
            scroll = next(s for s in scrolls if s.get("title") == selected_title)

            st.subheader(scroll.get("title", "Unnamed Scroll"))

            if st.button("Reconstruct Document", type="primary"):
                if use_blockfrost and not blockfrost_key:
                    st.error("Please provide a Blockfrost API key to proceed.")
                else:
                    with st.spinner("Fetching manifest & reconstructing..."):
                        try:
                            manifest = fetch_manifest(
                                scroll,
                                use_blockfrost=use_blockfrost,
                                bf_key=blockfrost_key,
                            )

                            data, content_type = reconstruct(
                                scroll,
                                manifest,
                                bf_key=blockfrost_key,
                            )

                            # Determine file extension
                            ext = "html" if "html" in content_type.lower() else "txt"
                            if "pdf" in content_type.lower():
                                ext = "pdf"
                            elif "json" in content_type.lower():
                                ext = "json"

                            filename = f"{selected_title.replace(' ', '_')}.{ext}"

                            st.success("Document reconstructed successfully!")

                            # Preview
                            if "html" in content_type.lower():
                                st.markdown(data.decode("utf-8", errors="replace"), unsafe_allow_html=True)
                            else:
                                preview_text = data.decode("utf-8", errors="replace")[:2000]
                                st.text_area("Content preview (first 2000 chars)", preview_text, height=300)

                            # Download button
                            st.download_button(
                                label="Download Document",
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
