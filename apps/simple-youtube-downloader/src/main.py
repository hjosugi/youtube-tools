import streamlit as st
import os
from download import download
from delete import delete
from util import remove_list_parameter

st.title("Youtube Downloader")
url = st.text_input("URL", "")
file_type = st.radio("FILE", ["mp4", "mp3"])

if st.button("Download"):
    if url != "":
        delete()
        url = remove_list_parameter(url)
        file_path = download(url, file_type)
        st.success(f"Success!")
        file = open(file_path, "rb")
        try:
            btn = st.download_button(
                label="Save",
                data=file,
                file_name=os.path.basename(file_path),
                mime="video/mp4" if file_type == "mp4" else "audio/mp3",
            )
        finally:
            st.cache_data.clear()
    else:
        st.error("Please enter a URL")
