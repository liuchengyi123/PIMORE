(function () {
  if (window.__harborCsFab) return;
  window.__harborCsFab = true;
  var origin = (window.HARBOR_H5_ORIGIN || "").replace(/\/$/, "");
  var pageHost = location.hostname || "";
  var pageIsLocal = pageHost === "127.0.0.1" || pageHost === "localhost";
  var originIsLocal = !origin || /127\.0\.0\.1|localhost/i.test(origin);
  if (!pageIsLocal && originIsLocal) {
    origin = location.origin;
  }
  if (!origin) {
    origin = location.origin;
  }

  function barePath(pathname) {
    var text = (pathname || "/").split("?")[0];
    if (text.charAt(0) !== "/") text = "/" + text;
    var codes = ["de", "es"];
    for (var i = 0; i < codes.length; i++) {
      var head = "/" + codes[i];
      if (text === head || text.indexOf(head + "/") === 0) {
        text = text.slice(head.length) || "/";
        break;
      }
    }
    if (text.length > 1 && text.charAt(text.length - 1) === "/") {
      text = text.slice(0, -1);
    }
    return text || "/";
  }

  /** Only PDP (/p/...) and account home (/account). Hide on balance/orders/etc. */
  function shouldShowFab() {
    var bare = barePath(location.pathname);
    if (bare === "/account") return true;
    if (bare.indexOf("/p/") === 0) return true;
    return false;
  }

  if (!shouldShowFab()) return;

  function pickSkuCtx() {
    var body = document.body;
    var sku = (body && body.getAttribute("data-cs-sku")) || "";
    var name = (body && body.getAttribute("data-cs-name")) || "";
    var image = (body && body.getAttribute("data-cs-image")) || "";
    var price = (body && body.getAttribute("data-cs-price")) || "";
    if (!sku) {
      var m = location.pathname.match(/\/p\/([^\/\?#]+)/);
      if (m) sku = decodeURIComponent(m[1]);
    }
    if (!sku) {
      var hidden = document.querySelector('#buy-form input[name="sku"], input[name="sku"]');
      if (hidden && hidden.value) sku = hidden.value;
    }
    if (!name) {
      var h1 = document.querySelector("h1, .sku-summary h1, .detail-pane h1");
      if (h1) name = (h1.textContent || "").trim();
    }
    if (!price) {
      var p = document.querySelector("#sku-price, .sku-summary .price, .price-row .price");
      if (p) price = (p.textContent || "").trim();
    }
    if (!image) {
      var img = document.querySelector("#gallery img, .gallery img, .stage img");
      if (img && img.src) image = img.src;
    }
    return { sku: sku, name: name, image: image, price: price };
  }

  function buildUrl() {
    var ctx = pickSkuCtx();
    var url = origin + "/chat";
    if (ctx.sku) {
      var q = ["sku=" + encodeURIComponent(ctx.sku)];
      if (ctx.name) q.push("name=" + encodeURIComponent(ctx.name));
      if (ctx.image) q.push("image=" + encodeURIComponent(ctx.image));
      if (ctx.price) q.push("price=" + encodeURIComponent(ctx.price));
      url += "?" + q.join("&");
    }
    return url;
  }

  var a = document.createElement("a");
  a.className = "harbor-cs-fab";
  a.href = buildUrl();
  a.target = "_blank";
  a.rel = "noopener";
  var zh = (document.documentElement.lang || "").toLowerCase().indexOf("zh") === 0
    || (document.body && /zh/i.test(document.body.getAttribute("data-lang") || ""))
    || /(?:^|;\s*)harbor_hl=zh(?:;|$)/i.test(document.cookie || "");
  a.setAttribute("aria-label", zh ? "客服" : "Customer support");
  a.innerHTML = '<span class="hcs-ico" aria-hidden="true">💬</span><span class="hcs-lab">'
    + (zh ? "客服" : "Chat") + "</span>";
  a.addEventListener("mouseenter", function () { a.href = buildUrl(); });
  a.addEventListener("focus", function () { a.href = buildUrl(); });
  document.body.appendChild(a);
})();