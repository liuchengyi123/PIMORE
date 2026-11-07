/* Harbor Function auth modal — stay on current page after login/register */
(function () {
  "use strict";

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function modalRoot() {
    return $("#hb-auth-modal");
  }

  function setMode(mode) {
    var root = modalRoot();
    if (!root) return;
    root.dataset.mode = mode === "register" ? "register" : "login";
    $all("[data-auth-pane]", root).forEach(function (pane) {
      pane.hidden = pane.getAttribute("data-auth-pane") !== root.dataset.mode;
    });
    var err = $("#hb-auth-error", root);
    if (err) {
      err.hidden = true;
      err.textContent = "";
    }
  }

  function openAuth(mode) {
    var root = modalRoot();
    if (!root) {
      var path = mode === "register" ? "/register" : "/login";
      var next = encodeURIComponent(location.pathname + location.search);
      location.href = path + "?next=" + next;
      return;
    }
    setMode(mode || "login");
    root.hidden = false;
    document.documentElement.classList.add("hb-auth-open");
    var focus = root.querySelector(
      '[data-auth-pane="' + root.dataset.mode + '"] input[name="email"]'
    );
    if (focus) setTimeout(function () { focus.focus(); }, 30);
  }

  function closeAuth() {
    var root = modalRoot();
    if (!root) return;
    root.hidden = true;
    document.documentElement.classList.remove("hb-auth-open");
  }

  function showError(msg) {
    var root = modalRoot();
    var err = $("#hb-auth-error", root);
    if (!err) return;
    err.textContent = msg || "Something went wrong";
    err.hidden = false;
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data || {} };
      });
    });
  }

  function onSuccess() {
    closeAuth();
    // Refresh in place so cart / wishlist / me / checkout pick up the session.
    location.reload();
  }

  function bindForm(form) {
    if (!form || form.__hbAuthBound) return;
    form.__hbAuthBound = true;
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var mode = form.getAttribute("data-auth-form");
      var email = (form.querySelector('[name="email"]') || {}).value || "";
      var password = (form.querySelector('[name="password"]') || {}).value || "";
      var url = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      var btn = form.querySelector('[type="submit"]');
      if (btn) btn.disabled = true;
      postJson(url, { email: email, password: password })
        .then(function (result) {
          if (btn) btn.disabled = false;
          if (result.data && result.data.ok) {
            onSuccess();
            return;
          }
          var code = (result.data && result.data.code) || "";
          var msg =
            (result.data && result.data.message) ||
            (code === "taken"
              ? "Email already registered"
              : code === "short"
              ? "Password must be at least 8 characters"
              : code === "email"
              ? "Enter a valid email"
              : code === "bad"
              ? "Incorrect email or password"
              : "Could not sign in");
          showError(msg);
        })
        .catch(function () {
          if (btn) btn.disabled = false;
          showError("Network error");
        });
    });
  }

  function interceptAuthLinks(ev) {
    var a = ev.target.closest && ev.target.closest("a[href]");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    try {
      var url = new URL(href, location.origin);
      if (url.origin !== location.origin) return;
      var path = url.pathname.replace(/\/+$/, "") || "/";
      if (path === "/login" || path === "/register") {
        // Allow deep-link pages when already on /login or /register.
        if (location.pathname === "/login" || location.pathname === "/register") {
          return;
        }
        // Modifier keys / new tab: keep default.
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || a.target === "_blank") {
          return;
        }
        ev.preventDefault();
        openAuth(path === "/register" ? "register" : "login");
      }
    } catch (e) {}
  }

  function boot() {
    var root = modalRoot();
    if (root) {
      $all("[data-auth-form]", root).forEach(bindForm);
      $all("[data-auth-close]", root).forEach(function (el) {
        el.addEventListener("click", function (ev) {
          ev.preventDefault();
          closeAuth();
        });
      });
      $all("[data-auth-switch]", root).forEach(function (el) {
        el.addEventListener("click", function (ev) {
          ev.preventDefault();
          setMode(el.getAttribute("data-auth-switch"));
        });
      });
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape" && !root.hidden) closeAuth();
      });
    }
    document.addEventListener("click", interceptAuthLinks);
    window.HarborAuth = { open: openAuth, close: closeAuth };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
