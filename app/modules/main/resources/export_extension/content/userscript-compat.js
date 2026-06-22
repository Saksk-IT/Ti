(() => {
  "use strict";

  if (typeof window.GM_addStyle !== "function") {
    window.GM_addStyle = (cssText) => {
      const style = document.createElement("style");
      style.textContent = String(cssText || "");
      (document.head || document.documentElement).appendChild(style);
      return style;
    };
  }

  if (typeof window.GM_setClipboard !== "function") {
    window.GM_setClipboard = (text) => {
      const value = String(text || "");
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(value).catch(() => legacyCopy(value));
        return;
      }
      legacyCopy(value);
    };
  }

  if (typeof window.GM_xmlhttpRequest !== "function") {
    window.GM_xmlhttpRequest = (details) => {
      const method = details && details.method ? details.method : "GET";
      const headers = details && details.headers ? details.headers : {};
      const timeout = Number(details && details.timeout ? details.timeout : 0);
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeoutId = timeout && controller
        ? window.setTimeout(() => controller.abort(), timeout)
        : null;

      fetch(String(details && details.url ? details.url : ""), {
        method,
        headers,
        body: details ? details.data : undefined,
        credentials: details && details.anonymous ? "omit" : "include",
        signal: controller ? controller.signal : undefined
      })
        .then((response) => response.text().then((responseText) => {
          if (timeoutId) window.clearTimeout(timeoutId);
          if (typeof details.onload === "function") {
            details.onload({
              status: response.status,
              statusText: response.statusText,
              responseText,
              finalUrl: response.url
            });
          }
        }))
        .catch((error) => {
          if (timeoutId) window.clearTimeout(timeoutId);
          const aborted = error && error.name === "AbortError";
          const handler = aborted ? details && details.ontimeout : details && details.onerror;
          if (typeof handler === "function") handler(error);
        });
    };
  }

  function legacyCopy(value) {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "readonly");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
    } finally {
      textarea.remove();
    }
  }
})();
