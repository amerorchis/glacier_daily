"""
This module provides a function to convert a string to an HTML-safe format.
"""

import html


def html_safe(input_string: str) -> str:
    """
    Convert a string to an HTML-safe format.

    Escapes HTML special characters (<, >, &, ", ') and then encodes
    non-ASCII characters as XML character references.

    Args:
        input_string (str): The string to be converted.

    Returns:
        str: The HTML-safe string.
    """
    escaped = html.escape(input_string)
    return escaped.encode("ascii", "xmlcharrefreplace").decode("utf-8")
