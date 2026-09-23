# YouTube transcript proxy

YouTube may block transcript requests from cloud-provider or rate-limited IP
addresses. In that case, configure a rotating residential proxy before starting
the API:

```env
YOUTUBE_HTTP_PROXY=http://username:password@proxy-host:port
YOUTUBE_HTTPS_PROXY=http://username:password@proxy-host:port
```

Either variable can be provided on its own; it will be used for both HTTP and
HTTPS requests. Standard `HTTP_PROXY` and `HTTPS_PROXY` variables are also
supported as fallbacks. Restart or redeploy the backend after changing these
values. The variable name is `YOUTUBE_HTTPS_PROXY` (HTTPS, not HHTPS).

For videos that require a signed-in YouTube session, export browser cookies in
Netscape `cookies.txt` format and point the backend to that file:

```env
YOUTUBE_COOKIES_FILE=/absolute/path/to/youtube-cookies.txt
```

Do not commit the cookies file. On a hosted backend, mount it as a secret file
and set `YOUTUBE_COOKIES_FILE` to the mounted path. Cookies can help with
sign-in checks, but an IP block or HTTP 429 still requires a different network
or a rotating residential proxy.
