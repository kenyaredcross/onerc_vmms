import React from "react";
import ReactDOM from "react-dom/client";
// react-router v7 consolidated its packages; ans-hub installs and imports
// `react-router-dom`, so this app does the same. The import source and the
// dependency in package.json must match.
import { BrowserRouter } from "react-router-dom";
import { FrappeProvider } from "frappe-react-sdk";
import App from "./App";
import "./index.css";

declare global {
  interface Window {
    frappe?: {
      boot?: {
        sitename?: string;
      };
    };
    csrf_token?: string;
  }
}

// Same-origin, cookie-session auth: no token props. The site name is injected by
// www/portal.py; when it is absent the SDK simply omits the header, which is the
// right answer on a single-site bench.
const getSiteName = (): string | undefined => window.frappe?.boot?.sitename;

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Failed to find the root element");
}

// The app answers under two names, and this is where it works out which one it
// was opened under.
//
// `/home` is the public address — what the site root redirects to, and what a
// person can be told out loud. `/portal` is the original one, kept live because
// it is in bookmarks and in the login round trip. Both are pointed at the same
// www page by `website_route_rules`, so the only thing that differs is the
// prefix react-router has to strip, and a basename that did not match the
// address would leave the router rendering nothing at all.
//
// Anything else — the bare root, if the redirect is ever bypassed — is put on
// the public name before the first render rather than after it, so nobody sees
// a frame of the wrong page.
const APP_ROOT = "/portal";
const PUBLIC_ROOT = "/home";

const { pathname, search, hash } = window.location;
const under = (root: string) => pathname === root || pathname.startsWith(`${root}/`);

const BASENAME = under(APP_ROOT) ? APP_ROOT : PUBLIC_ROOT;

if (!under(BASENAME)) {
  window.history.replaceState(null, "", `${BASENAME}${search}${hash}`);
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <FrappeProvider url={window.location.origin} siteName={getSiteName()}>
      <BrowserRouter basename={BASENAME}>
        <App />
      </BrowserRouter>
    </FrappeProvider>
  </React.StrictMode>,
);
