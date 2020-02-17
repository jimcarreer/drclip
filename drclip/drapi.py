import re
import requests
from typing import Union

from drclip.creds import DockerCredentials


class RegistryAPIError(Exception):
    """Base class for all registry errors"""
    pass


class UnexpectedPageLink(Exception):
    """Raised when there's an unexpected Link header in an API that's expected to be paginated"""
    pass


class RegistryV2API:

    def __init__(self, registry: str, credentials: DockerCredentials = None):
        """
        Implements interface into V2 docker registry

        :param registry: the registry url to which this object will communicate
        :param credentials: provides credentials to use for authentication to registry
        """
        self._scheme = 'https'
        self._prefix = 'v2'
        self._registry = registry
        self._credentials = credentials if credentials else DockerCredentials()
        self._session = requests.Session()

    def url(self, api: str, prefix: bool = True) -> str:
        """
        Builds the full url required to call the given api

        :param api: the api to build the url for
        :param prefix: add api prefix to the given api string
        :return: full url to call an api with
        """
        if prefix:
            return f'{self._scheme}://{self._registry}/{self._prefix}/{api.strip("/")}'
        return f'{self._scheme}://{self._registry}/{api.strip("/")}'

    def raw_request(self, method: str, url: str, **kwargs: dict):
        """
        Makes an HTTP request using the underlying request session instance

        :param method: the HTTP method to make the request with
        :param url: the url to make the request with
        :param kwargs: keyword arguments to pass to the underlying request session method
        :raises ValueError: if method is not one of 'get', 'post', 'put', 'patch', or 'head'
        :return: the request response object fulfilling the request
        """
        if method not in ['get', 'post', 'put', 'patch', 'head', 'delete']:
            raise ValueError(f'Bad HTTP method {method}')
        method = getattr(self._session, method)
        kwargs.update(auth=self._credentials.get_login(self._registry))
        return method(url, **kwargs)

    def get(self, api: str = '', params: Union[dict, None] = None) -> dict:
        """
        Call a GET API against the registry

        :param api: (optional) the api to call, defaults to '' which just calls the /v2/ endpoint for version checking
        :param params: (optional) query parameters, defaults to None (no parameters)
        :return: payload data decoded as json
        """
        res = self.raw_request('get', self.url(api), params=params)
        res.raise_for_status()
        return res.json()

    def head(self, api: str = '', params: Union[dict, None] = None) -> dict:
        """
        Call a HEAD API against the registry

        :param api: (optional) the api to call, defaults to '' which just calls the /v2/ endpoint for version checking
        :param params: (optional) query parameters, defaults to None (no parameters)
        :return: response headers
        """
        res = self.raw_request('head', self.url(api), params=params)
        res.raise_for_status()
        return res.headers

    def delete(self, api: str, params: Union[dict, None] = None):
        """
        Call a DELETE API against the registry

        :param api: the api to call
        :param params: (optional) query parameters, defaults to None (no parameters)
        :return: response headers
        """
        res = self.raw_request('delete', self.url(api), params=params)
        res.raise_for_status()


class Paginated:

    NEXT_REGEX = re.compile(r'^</v2/.+>$')

    def __init__(self, registry_api: RegistryV2API, api_path: str, params: dict = None):
        """
        Implements an iterator for a paginated API response

        :param registry_api: a registry api object to use to make api calls
        :param api_path: the paginated api path to call
        :param params: query parameters to send with the first request
        """
        self._last = None
        self._next = None
        self._registry_api = registry_api
        self._params = params
        self._api_path = api_path

    @staticmethod
    def extract_next(link: str) -> Union[str, None]:
        """
        The V2 docker registry returns pagination links in the form of a header "Links" with a value like:

            '</v2/some/api/path?query_param=x>; rel="next"'

        This function extracts the link to use in a subsequent request.


        :param link: the raw link header from a previous pages response object
        :raises UnexpectedPageLink: if link does not appear to be correctly formed
        :return: the next link to follow for a paginated response, None if link is empty
        """
        if not link.strip():
            return None
        parts = link.split('; ')
        if len(parts) != 2 or parts[1] != 'rel="next"' or not Paginated.NEXT_REGEX.match(parts[0]):
            raise UnexpectedPageLink(f'Strange link header in paginated api: {link}')
        return parts[0].replace('<', '').replace('>', '')

    def __iter__(self):
        return self

    def __next__(self):
        if not self._last:  # First page
            url = self._registry_api.url(api=self._api_path)
        elif self._next:  # All other pages
            self._params = None  # Next will encode any params we sent/need with first page
            url = self._registry_api.url(api=self._next, prefix=False)
        else:  # We're done
            raise StopIteration
        self._last = self._registry_api.raw_request('get', url, params=self._params)
        self._last.raise_for_status()
        ret = self._last.json()
        self._next = self.extract_next(self._last.headers.get('Link', ''))
        return ret
