from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def remove_list_parameter(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    if "list" in query_params:
        del query_params["list"]

    new_query_string = urlencode(query_params, doseq=True)

    new_url = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query_string,
            parsed_url.fragment,
        )
    )

    return new_url
