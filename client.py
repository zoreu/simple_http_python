import json as json_
import chardet
import six

if six.PY2:
    import httplib as http_client
    from urlparse import urlparse, urlencode
else:
    import http.client as http_client
    from urllib.parse import urlparse, urlencode

class HTTP(object):
    def __init__(self, url, headers=None):
        self.url = url
        self._headers = headers if headers else {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
        self._text = None
        self._content = None
        self.status_code = 0
        self.response = None  # To store the response object
        self.conn = None  # Store connection object
        self._head = False
        self._cookies = {}  # To store cookies
        self._encoding = None  # To store detected encoding

    def send_request(self, method, url, headers=None, data=None, json=None, max_redirects=5, timeout=5, cookies=None):
        if headers is None:
            headers = {}

        if method == 'HEAD':
            self._head = True

        parsed_url = urlparse(url)
        host = parsed_url.hostname
        path = parsed_url.path
        port = parsed_url.port
        if not path:
            path = '/'
        gets = parsed_url.query
        path = path + '?' + gets if gets else path

        try:
            if parsed_url.scheme == 'https':
                self.conn = http_client.HTTPSConnection(host, timeout=timeout)
            else:
                if port:
                    self.conn = http_client.HTTPConnection(host, port=port, timeout=timeout)
                else:
                    self.conn = http_client.HTTPConnection(host, timeout=timeout)

            # Merge cookies with headers
            if cookies:
                headers.update({'Cookie': '; '.join([f'{key}={value}' for key, value in cookies.items()])})

            # Handle data and json payloads
            if json is not None:
                data = json_.dumps(json)
                headers['Content-Type'] = 'application/json'
            elif data is not None:
                data = urlencode(data)  # Convert dictionary to urlencoded string
                headers['Content-Type'] = 'application/x-www-form-urlencoded'

            self.conn.request(method, path, body=data.encode() if data is not None else None, headers=headers)
            self.response = self.conn.getresponse()
            self.status_code = self.response.status

            # Handling cookies
            self._cookies.update(self._extract_cookies(self.response.getheaders()))

            # Handling redirects
            if 300 <= self.response.status < 400 and 'Location' in dict(self.response.getheaders()) and max_redirects > 0:
                new_location = self.response.getheader('Location')
                self.url = new_location
                self.conn.close()
                return self.send_request(method, new_location, headers, data, json, max_redirects - 1, timeout, cookies)

            # Don't read the response content yet for HEAD requests
            if self._head:
                self.conn.close()

        except Exception as e:
            print(e)

        return self

    def json(self):
        try:
            if self._content is None:
                self._content = self.response.read()
            d = json_.loads(self._content)
            self.conn.close()
            return d
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            return {}

    @staticmethod
    def get(url, headers=None, timeout=5, cookies=None):
        instance = HTTP(url, headers)
        instance.send_request('GET', instance.url, instance._headers, timeout=timeout, cookies=cookies)
        return instance

    @staticmethod
    def post(url, headers=None, data=None, json=None, timeout=5, cookies=None):
        instance = HTTP(url, headers)
        instance.send_request('POST', instance.url, instance._headers, data=data, json=json, timeout=timeout, cookies=cookies)
        return instance

    @staticmethod
    def head(url, headers=None, timeout=5, cookies=None):
        instance = HTTP(url, headers)
        instance.send_request('HEAD', instance.url, instance._headers, timeout=timeout, cookies=cookies)
        return instance

    @property
    def content(self):
        if self._content is None and self.response is not None and not self._head:
            self._content = self.response.read()
            self.conn.close()
        return self._content

    @property
    def text(self):
        if self._text is None and not self._head:
            if self._content is None:
                self._content = self.response.read()
            if self._encoding is None:
                self._encoding = self._detect_encoding()
            self._text = self._content.decode(self._encoding)
        return self._text

    @property
    def cookies(self):
        return self._cookies

    @property
    def headers(self):
        if self.response is not None:
            return dict(self.response.getheaders())
        return {}

    def iter_content(self, chunk_size=1024):
        """Generator to read the response content in chunks."""
        if self.response:
            try:
                while True:
                    chunk = self.response.read(chunk_size)
                    if not chunk:
                        self.conn.close()
                        break
                    yield chunk
            except Exception as e:
                print(f"Error while iterating content: {e}")
        else:
            print("No response object to iterate")

    def _extract_cookies(self, headers):
        cookies = {}
        for header, value in headers:
            if header.lower() == 'set-cookie':
                cookie_parts = value.split(';')[0].split('=')
                key = cookie_parts[0].strip()
                value = '='.join(cookie_parts[1:]).strip()
                cookies[key] = value
        return cookies

    def _detect_encoding(self):
        response = self.response
        content_type = response.getheader('Content-Type', '').lower()
        charset_index = content_type.find('charset=')
        if charset_index != -1:
            encoding = content_type[charset_index + 8:]
            return encoding.strip()

        # Fallback to chardet if charset is not found in Content-Type header
        try:
            raw_data = response.read()
            encoding = chardet.detect(raw_data)['encoding']
            return encoding
        except Exception as e:
            print(f"Failed to detect encoding: {e}")
            return None

# Example usage
url = 'https://google.com'
r = HTTP.get(url)
print(r.text)
