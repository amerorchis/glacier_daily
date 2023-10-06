def html_safe(input_string):
    return input_string.encode('ascii', 'xmlcharrefreplace').decode('utf-8')
