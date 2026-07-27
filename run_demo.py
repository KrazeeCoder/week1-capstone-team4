"""Launches the Streamlit demo: `python run_demo.py`.

Works around a Windows-only ssl bug where some machines have a certificate
in the Windows cert store with malformed ASN.1 data. tornado (a Streamlit
dependency) eagerly builds a default SSLContext at import time and Python's
ssl module crashes trying to parse every cert in the store, even though the
demo itself never uses HTTPS. Patching load_default_certs to skip
unparseable certs avoids the crash without touching Windows cert store
config.
"""
import ssl
import sys

_original_load_default_certs = ssl.SSLContext.load_default_certs


def _tolerant_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
    try:
        return _original_load_default_certs(self, purpose)
    except ssl.SSLError:
        pass


ssl.SSLContext.load_default_certs = _tolerant_load_default_certs

from streamlit.web.cli import main  # noqa: E402  (must import after the patch above)

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "streamlit_demo.py", *sys.argv[1:]]
    sys.exit(main())
