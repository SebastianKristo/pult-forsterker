"""QR-kode med enhetens adresse (oppsett fra Skjold-appen: «Skann QR-kode på skjermen»).
Bruker qrcode-pakken (pip, ren Python); uten den vises bare adressen som tekst."""
import socket


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except Exception:
        return ""
    finally:
        s.close()


def matrix(text):
    """Liste med rader av bool (True = mørk modul), uten stillesone. None hvis qrcode mangler."""
    try:
        import qrcode
    except ImportError:
        return None
    q = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, border=0)
    q.add_data(text); q.make(fit=True)
    return q.get_matrix()


def draw(c, m, x, y, mod, dark, light):
    """Tegn matrisen med stillesone (2 moduler) på lerretet c fra (x, y), mod piksler per modul."""
    n = len(m); q = 2
    c.rect(x, y, (n + 2 * q) * mod, (n + 2 * q) * mod, light)
    for r, row in enumerate(m):
        for k, v in enumerate(row):
            if v: c.rect(x + (k + q) * mod, y + (r + q) * mod, mod, mod, dark)
    return (n + 2 * q) * mod
