"""
This module provides a function to encode non-ASCII characters for HTML email compatibility.
"""


def html_safe(input_string: str) -> str:
    """
    Encode non-ASCII characters as XML character references for email compatibility.

    Note: This does NOT escape HTML tags — template fields intentionally contain
    pre-sanitized HTML markup that must be rendered, not escaped.

    Args:
        input_string (str): The string to be converted.

    Returns:
        str: The string with non-ASCII characters encoded as XML character references.
    """
    return input_string.encode("ascii", "xmlcharrefreplace").decode("utf-8")
