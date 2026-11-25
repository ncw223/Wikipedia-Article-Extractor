
import streamlit as st

from wikipedia_extractor_core import (
    WikipediaExtractor,
    format_txt,
    safe_filename,
    numbered_filename
)

st.set_page_config(
    page_title="Wikipedia Extractor",
    layout="wide"
)


# Initialize session state
default_state = {
    "topic": None,
    "article": None,
    "titles": [],
    "selected": [],
    "sections": [],
    "saved_path": None,
    "pending_overwrite": None,
    "pending_filename": None,
    "downloaded_filenames": []
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value


# Download callback
def record_download(filename):
    if filename not in st.session_state.downloaded_filenames:
        st.session_state.downloaded_filenames.append(filename)


# Sidebar
with st.sidebar:
    st.header("Navigation")

    if st.button("Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.rerun()


st.title("Wikipedia Article Extractor")


# How to use this app
with st.expander("How to use this app"):
    st.markdown("""
1. Enter a topic and click Search.
2. Select the sections you want.
3. Click Extract to preview the content.
4. Click Download .txt to save the content.
""")


# Progress indicator
progress = st.container()

with progress:
    progress_slots = [
        column.empty() for column in st.columns(4)
    ]


# Stage 1 - Search
with st.form("search_form"):
    topic_input = st.text_input("Enter a topic")
    search_submitted = st.form_submit_button("Search")


if search_submitted:
    st.session_state.topic = topic_input.strip()
    st.session_state.article = None
    st.session_state.titles = []
    st.session_state.selected = []
    st.session_state.sections = []

    st.session_state.pop("section_picker", None)

    if not st.session_state.topic:
        st.warning("Please enter a Wikipedia topic.")

    else:
        with st.spinner("Searching Wikipedia..."):
            article = WikipediaExtractor(
                st.session_state.topic
            )

        st.session_state.article = article

        if not article.error:
            st.session_state.titles = [
                s["title"] for s in article.sections
            ]


article = st.session_state.article

if article is not None:

    if article.error:
        st.error(article.error)

    else:
        st.success(f"Article found: {article.title}")
        st.write(article.url)

        if not st.session_state.titles:
            st.warning("No article sections found.")


# Stage 2 - Select
if st.session_state.titles:

    st.subheader("Select Article Sections")

    st.session_state.selected = st.multiselect(
        "Choose the sections you want to extract",
        options=st.session_state.titles,
        default=st.session_state.selected,
        key="section_picker"
    )


    # Stage 3 - Extract
    if st.button("Extract"):

        if not st.session_state.selected:
            st.warning(
                "Please select at least one section."
            )

        else:
            st.session_state.sections = []

            with st.spinner("Extracting selected sections..."):

                for title in st.session_state.selected:

                    number = (
                        st.session_state.titles.index(title) + 1
                    )

                    content = article.extract_selected([number])

                    if article.error:
                        st.error(article.error)

                    else:
                        st.session_state.sections.append({
                            "title": title,
                            "content": content
                        })


# Stage 4 - Preview
if st.session_state.sections:

    st.subheader("Extracted Content Preview")

    with st.container(border=True):

        for section in st.session_state.sections:

            st.markdown(f"### {section['title']}")

            content = section["content"]

            header = (
                f"\n{'=' * 50}\n"
                f"{section['title']}\n"
                f"{'=' * 50}"
            )

            if content.startswith(header):
                content = content[len(header):].strip()

            if not content.strip():
                st.caption("(no extractable content)")

            else:
                st.text(content)

            st.divider()


    # Stage 5 - Download
    proposed_filename = (
        safe_filename(article.title) + ".txt"
    )

    filename = numbered_filename(
        proposed_filename,
        st.session_state.downloaded_filenames
    )

    if proposed_filename in st.session_state.downloaded_filenames:

        if filename == safe_filename(article.title) + " (2).txt":
            st.warning(
                "You already downloaded a file with this "
                "name in this session. Downloading again "
                "will add (2) to the name."
            )

        else:
            st.warning(
                f"You already downloaded a file with this "
                f"name in this session. "
                f"The next filename is {filename}."
            )

    st.download_button(
        label="Download .txt",
        data=format_txt(
            article.title,
            article.url,
            st.session_state.sections
        ),
        file_name=filename,
        mime="text/plain",
        key="download_btn",
        on_click=record_download,
        args=(filename,)
    )


# Update progress after processing the current interaction
for slot, (label, key) in zip(progress_slots, [
    ("Search", "topic"),
    ("Select", "titles"),
    ("Extract", "sections"),
    ("Download", "downloaded_filenames")
]):
    mark = "✅" if st.session_state[key] else "⬜"
    slot.caption(f"{mark} {label}")


# Wikipedia attribution
st.caption("Content from Wikipedia, CC BY-SA 4.0.")


# Debugging
st.write(st.session_state)
