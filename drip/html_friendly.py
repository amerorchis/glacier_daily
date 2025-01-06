"""
This module provides a function to convert a string to an HTML-safe format.
"""

def html_safe(input_string):
    """
    Convert a string to an HTML-safe format.

    Args:
        input_string (str): The string to be converted.

    Returns:
        str: The HTML-safe string.
    """
    return input_string.encode('ascii', 'xmlcharrefreplace').decode('utf-8')
