"""Open the shared Streamlit Community Cloud app in the default browser."""

import webbrowser


APP_URL = "https://uetcs2046-7nhom-2git-nrjkk29yye8nfmfqpkg4cs.streamlit.app/"


def main() -> int:
    """Open the deployed app instead of starting a local Streamlit server."""
    if not webbrowser.open(APP_URL, new=2):
        print(f"Không mở được trình duyệt. Hãy truy cập thủ công: {APP_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
