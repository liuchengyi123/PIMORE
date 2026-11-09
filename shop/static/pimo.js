(function () {
  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }
  function tick() {
    document.querySelectorAll("[data-pimo-ends]").forEach(function (node) {
      var raw = node.getAttribute("data-pimo-ends") || "";
      var end = Date.parse(raw);
      if (!end) return;
      var left = Math.max(0, end - Date.now());
      var s = Math.floor(left / 1000);
      var h = Math.floor(s / 3600);
      var m = Math.floor((s % 3600) / 60);
      var sec = s % 60;
      var num = node.querySelector(".pimo-clock-num");
      if (num) num.textContent = pad(h) + " : " + pad(m) + " : " + pad(sec);
    });
  }
  tick();
  setInterval(tick, 1000);

  function paintCount(count) {
    document.querySelectorAll("[data-pimo-count]").forEach(function (node) {
      var n = Number(count) || 0;
      node.textContent = String(n);
      node.hidden = n <= 0;
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || !form.classList || !form.classList.contains("pimo-add")) return;
    event.preventDefault();
    var body = new FormData(form);
    body.set("ajax", "1");
    var button = form.querySelector("button");
    if (button) button.disabled = true;
    fetch(form.action, {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: { "X-Harbor-Ajax": "1", Accept: "application/json" }
    }).then(function (res) {
      return res.json();
    }).then(function (data) {
      if (data && data.ok) paintCount(data.cart_count);
    }).catch(function () {}).then(function () {
      if (button) button.disabled = false;
    });
  });
})();
