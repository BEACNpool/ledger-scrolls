import streamlit as st
import json
from pathlib import Path

from viewer import (
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
    st.caption("Permissionless, immutable documents (and images) on Cardano")

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Settings")

        use_registry = st.checkbox("Use on-chain registry", value=True)

        use_blockfrost = st.checkbox("Use Blockfrost for metadata (faster)", value=True)

        blockfrost_key = None
        if use_blockfrost:
            blockfrost_key = st.text_input(
                "Blockfrost Project ID / API Key",
                type="password",
                help="Required when using Blockfrost mode",
                key="bf_key_input",
            )

        custom_registry_file = st.file_uploader(
            "Optional: custom registry JSON",
            type=["json"],
            help="Upload uncompressed registry datum content",
        )

        if use_blockfrost and not blockfrost_key:
            st.warning("Blockfrost API key required in Blockfrost mode.")

    # ── Main content ─────────────────────────────────────────────────────────
    try:
        # Load scrolls
        if custom_registry_file is not None:
            custom_data = json.load(custom_registry_file)
            scrolls = custom_data.get("scrolls", [])
            st.info("Using custom uploaded registry JSON")
        else:
            scrolls = get_scrolls(use_registry=use_registry)

        if not scrolls:
            st.warning("No scrolls found → using built-in demo entries.")
            scrolls = DEFAULT_SCROLLS.copy()

        # Display selector
        scroll_titles = [s.get("title", f"Untitled ({s.get('id', '-')})") for s in scrolls]
        selected_title = st.selectbox("Select document / image", scroll_titles)

        if selected_title:
            scroll = next(s for s in scrolls if s.get("title") == selected_title)

            st.subheader(scroll.get("title", "Unnamed Scroll"))

            if st.button("Load / Reconstruct", type="primary"):
                if use_blockfrost and not blockfrost_key:
                    st.error("Blockfrost API key is required in this mode.")
                else:
                    with st.spinner("Loading..."):
                        try:
                            if scroll.get("kind") == "inline_png":
                                manifest = {}  # not needed
                            else:
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

                            # Determine extension for download
                            ext_map = {
                                "text/html": "html",
                                "text/plain": "txt",
                                "application/pdf": "pdf",
                                "image/png": "png",
                            }
                            ext = ext_map.get(content_type, "bin")

                            filename = f"{selected_title.replace(' ', '_')}.{ext}"

                            st.success("Content loaded successfully!")

                            # ── Rendering logic ──────────────────────────────────
                            ct = content_type.lower()

                            if ct.startswith("image/"):
                                st.image(data, use_column_width=True)

                            elif "html" in ct:
                                try:
                                    html_content = data.decode("utf-8", errors="replace")
                                    st.markdown(html_content, unsafe_allow_html=True)
                                except:
                                    st.error("Failed to decode HTML content")

                            else:
                                # Text / other fallback
                                try:
                                    preview = data.decode("utf-8", errors="replace")[:4000]
                                    st.text_area("Content preview", preview, height=400)
                                except:
                                    st.info("Binary / non-text content loaded (no preview)")

                            # Always offer download
                            st.download_button(
                                label="Download",
                                data=data,
                                file_name=filename,
                                mime=content_type,
                            )

                        except Exception as e:
                            st.error(f"Loading failed\n\n{str(e)}")

    except Exception as e:
        st.error(f"Cannot load scroll list / registry\n\n{str(e)}")


if __name__ == "__main__":
    main()