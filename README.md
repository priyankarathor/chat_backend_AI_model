# YouTube transcript proxy

YouTube may block transcript requests from cloud-provider or rate-limited IP
addresses. In that case, configure a rotating residential proxy before starting
the API:

```env
YOUTUBE_HTTP_PROXY=http://username:password@proxy-host:port
YOUTUBE_HTTPS_PROXY=http://username:password@proxy-host:port
```

Either variable can be provided on its own; it will be used for both HTTP and
HTTPS requests. Restart the backend after changing these values.
