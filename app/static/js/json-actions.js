(() => {
  function applyPatch(patch) {
    Object.entries(patch || {}).forEach(([selector, changes]) => {
      const target = document.querySelector(selector);
      if (!target || !changes || typeof changes !== "object") {
        return;
      }

      Object.entries(changes).forEach(([property, value]) => {
        try {
          target[property] = value;
        } catch (error) {
          console.warn("json-actions: failed to apply patch", selector, property, error);
        }
      });
    });
  }

  function requestUrlFor(element) {
    const configured = element.getAttribute("url");
    if (!configured) {
      return null;
    }

    if (element.tagName === "FORM") {
      const url = new URL(configured, window.location.origin);
      const formData = new FormData(element);
      const params = new URLSearchParams(formData);
      params.forEach((value, key) => {
        url.searchParams.set(key, value);
      });
      return url.toString();
    }

    return new URL(configured, window.location.origin).toString();
  }

  function updateHistory(element, requestUrl) {
    if (element.tagName !== "A") {
      return;
    }

    const nextUrl = element.getAttribute("href") || requestUrl;
    if (!nextUrl) {
      return;
    }

    window.history.pushState({ url: nextUrl }, "", nextUrl);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  async function fetchPatch(requestUrl) {
    const response = await window.fetch(requestUrl, {
      headers: {
        Accept: "application/json",
        "X-Requested-With": "json-runtime",
      },
    });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    return response.json();
  }

  function bindElement(element) {
    const eventName = element.getAttribute("fn");
    if (!eventName) {
      return;
    }

    const handler = async (event) => {
      const requestUrl = requestUrlFor(element);
      if (!requestUrl) {
        return;
      }

      if (event) {
        event.preventDefault();
      }

      try {
        const patch = await fetchPatch(requestUrl);
        applyPatch(patch);
        updateHistory(element, requestUrl);
        window.bindJsonActions();
      } catch (error) {
        if (element.tagName === "A" && element.href) {
          window.location.assign(element.href);
          return;
        }

        if (element.tagName === "FORM") {
          element.submit();
          return;
        }

        console.warn("json-actions: falling back", error);
      }
    };

    element[eventName] = handler;

    if (element.tagName === "FORM" && eventName !== "onsubmit") {
      element.onsubmit = handler;
    }
  }

  window.bindJsonActions = () => {
    document.querySelectorAll("[url][fn]").forEach(bindElement);
  };

  window.addEventListener("popstate", async () => {
    try {
      const patch = await fetchPatch(window.location.href);
      applyPatch(patch);
      window.bindJsonActions();
      window.scrollTo({ top: 0, behavior: "auto" });
    } catch (error) {
      window.location.reload();
    }
  });

  window.addEventListener("load", () => {
    window.bindJsonActions();
  });
})();
