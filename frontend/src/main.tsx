import { lazy, StrictMode, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { MarketingSite } from "./marketing/site";
import { marketingPath } from "./marketing/routes";
import "./styles.css";

const Workspace = lazy(() => import("./App"));
const PublicOrderPage = lazy(() =>
  import("./public").then(({ PublicOrderPage }) => ({
    default: PublicOrderPage,
  })),
);

function App() {
  const tracking = location.pathname.match(/^\/track\/([^/]+)\/?$/);
  if (tracking) return <PublicOrderPage token={tracking[1]} />;
  const path = marketingPath(location);
  return path === null ? <Workspace /> : <MarketingSite path={path} />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Suspense
      fallback={
        <div className="loading-screen" role="status">
          Загрузка…
        </div>
      }
    >
      <App />
    </Suspense>
  </StrictMode>,
);

import "./reference.css";
import "./parity.css";
import "@fontsource/golos-text/400.css";
import "@fontsource/golos-text/500.css";
import "@fontsource/golos-text/600.css";
import "@fontsource/golos-text/700.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./chat-layout.css";
import "./chat-folders.css";
import "./chat-mobile.css";
import "./mobile-workspace.css";
import "./chat-viewport.css";
