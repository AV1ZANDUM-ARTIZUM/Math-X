# Math-X Proxy Pro

A browser-only version of the Math-X Proxy Pro interface. It is made from plain HTML, CSS and JavaScript, so the frontend does **not** need Python and can be hosted on GitHub Pages.

## Browser-only features
- Responsive URL bar
- Direct iframe viewer
- Reader mode for pages that can be fetched by the configured text-reader service
- Open in a new tab
- Fullscreen viewer
- Quick links
- Clear/reset controls
- No API keys in the frontend
- No arbitrary TCP tunneling
- No local Python server required for the static version

## GitHub Pages
Publish the `proxy-pro` folder as the site root, or copy its three files (`index.html`, `style.css`, `script.js`) into the Pages root.

### Important limitation
A normal web page cannot freely fetch every other website because of browser CORS rules, and many sites also block iframe embedding. JavaScript alone therefore cannot be a universal web proxy. Reader mode uses a third-party text-reading endpoint and may not work for every destination.

For a true universal proxy, a server-side component is still required. The original Flask implementation remains in this repository for that use case.

## Use
Open `index.html`, enter an `https://` or `http://` address, and choose **Go**, **Reader**, or **Open tab**.

Use responsibly and only access sites you are permitted to access.
