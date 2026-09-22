from qt_api import QByteArray





def str_to_bytes(string):
    """ This is required to save Qt byte arrays into a base64 string (to save screen preferences) """
    return QByteArray.fromBase64(string.encode("utf-8"))


def bytes_to_str(bytes):
    """ This is required to load base64 Qt byte array strings into a Qt byte array (to load screen preferences) """
    return bytes.toBase64().data().decode("utf-8")


def model_index_sibling_at_column(index, column):
    """Return a sibling index for a column across old/new Qt bindings."""
    sibling_at_column = getattr(index, "siblingAtColumn", None)
    if callable(sibling_at_column):
        return sibling_at_column(column)
    return index.sibling(index.row(), column)


def font_metrics_horizontal_advance(metrics, text):
    """Measure text width across old/new Qt bindings."""
    horizontal_advance = getattr(metrics, "horizontalAdvance", None)
    if callable(horizontal_advance):
        return horizontal_advance(text)
    return metrics.width(text)
