(function () {
  function fillRain(node) {
    var count = Number(node.getAttribute("data-coins") || node.getAttribute("data-sparks") || 12);
    var up = node.classList.contains("spark");
    for (var i = 0; i < count; i += 1) {
      var bit = document.createElement("i");
      bit.style.left = Math.round(Math.random() * 100) + "%";
      bit.style.animationDuration = (up ? 3.5 : 2.4) + Math.random() * 2.4 + "s";
      bit.style.animationDelay = (-Math.random() * 4) + "s";
      if (!up) bit.style.width = bit.style.height = 10 + Math.round(Math.random() * 12) + "px";
      node.appendChild(bit);
    }
  }
  document.querySelectorAll(".rain, .spark").forEach(fillRain);

  function burst(id) {
    var node = document.querySelector(id);
    if (!node) return;
    node.classList.remove("is-open");
    void node.offsetWidth;
    node.classList.add("is-open");
  }

  var pop = document.getElementById("pop");
  var root = document.querySelector("[data-pop]");
  if (pop && root && root.getAttribute("data-pop") === "1") {
    window.setTimeout(function () { pop.classList.add("show"); }, 280);
    burst("#packet");
    burst("#device");
    burst("#medal");
  }
  document.querySelectorAll("[data-close]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (pop) pop.classList.remove("show");
    });
  });

  var form = document.getElementById("share-form");
  var seal = document.getElementById("seal");
  function arm(targetForm) {
    if (!targetForm) return;
    targetForm.addEventListener("submit", function (event) {
      if (targetForm.getAttribute("data-go") === "1") return;
      var email = targetForm.querySelector("input[name=email]");
      if (email && email.value.indexOf("@") < 0) return;
      event.preventDefault();
      burst("#packet");
      burst("#device");
      targetForm.setAttribute("data-go", "1");
      window.setTimeout(function () { targetForm.submit(); }, 650);
    });
  }
  arm(form);
  arm(document.getElementById("install-form"));
  if (seal && form) {
    seal.addEventListener("click", function () {
      var email = form.querySelector("input[name=email]");
      if (!email || email.value.indexOf("@") < 0) {
        if (email) email.focus();
        var body = document.querySelector(".packet-body");
        if (body) {
          body.animate([{ transform: "translateX(0)" }, { transform: "translateX(-8px)" }, { transform: "translateX(8px)" }, { transform: "translateX(0)" }], { duration: 360 });
        }
        return;
      }
      if (form.requestSubmit) form.requestSubmit();
      else form.submit();
    });
  }

  var copy = document.getElementById("copy");
  if (copy) {
    copy.addEventListener("click", function () {
      var link = document.getElementById("invite");
      var text = link ? link.textContent : "";
      var done = function () { copy.textContent = copy.getAttribute("data-done"); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done);
      else done();
    });
  }

  document.querySelectorAll("[data-replay]").forEach(function (button) {
    button.addEventListener("click", function () {
      burst(button.getAttribute("data-replay"));
      if (pop) {
        pop.classList.remove("show");
        window.setTimeout(function () { pop.classList.add("show"); }, 500);
      }
    });
  });

  var preview = document.getElementById("stamp-preview");
  if (preview && pop) {
    preview.addEventListener("click", function () {
      var today = document.querySelector(".lantern-week .today");
      if (today) today.classList.add("hit");
      burst("#medal");
      pop.classList.add("show");
    });
  }

  var deferred = null;
  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferred = event;
    var steps = document.getElementById("install-steps");
    if (steps) steps.hidden = true;
  });
  var install = document.getElementById("install-form");
  if (install) {
    install.addEventListener("submit", function (event) {
      if (!deferred || install.getAttribute("data-go") === "1") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      deferred.prompt();
      deferred.userChoice.then(function (choice) {
        deferred = null;
        if (choice.outcome === "accepted") {
          install.setAttribute("data-go", "1");
          burst("#device");
          window.setTimeout(function () { install.submit(); }, 600);
        }
      });
    }, true);
  }

  if ("serviceWorker" in navigator && document.querySelector("[data-mode=install]")) {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  }
})();
