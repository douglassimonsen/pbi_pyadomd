def _is_encoded_char(val: str) -> bool:
    UTF_ENCODED_LEN = 5
    start, body = val[0], val[1:]
    return (
        len(val) == UTF_ENCODED_LEN
        and start == "x"
        and all(c in "0123456789ABCDEF" for c in body)
    )

def _decode_name(name: str) -> str:
    """Processes names to decode any encoded characters within an XML-safe string."""
    name_parts = name.split("_")
    for i, e in enumerate(name_parts):
        if _is_encoded_char(e):
            name_parts[i] = chr(int(e[1:], 16))
    return "_".join(name_parts)
