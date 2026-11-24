/* dc-lite: renders a Claude Design (.dc.html) page outside the Design canvas.
   Supports what BoothMate's landing page uses: {{path}} in text and
   attributes, <sc-for list as>, <sc-if value>, on* handlers, setState.
   DOM updates go through morphdom so animations and focus survive re-renders. */
(function () {
  "use strict";
  var RE = /\{\{([^}]+)\}\}/g;
  var WHOLE = /^\s*\{\{([^}]+)\}\}\s*$/;

  function lookup(scope, expr) {
    expr = String(expr).trim();
    if (expr === "false") return false;
    if (expr === "true") return true;
    return expr.split(".").reduce(function (o, k) { return o == null ? undefined : o[k]; }, scope);
  }
  function interp(str, scope) {
    return str.replace(RE, function (_, e) { var v = lookup(scope, e); return v == null ? "" : String(v); });
  }
  function exprOf(attr) { var m = WHOLE.exec(attr || ""); return m ? m[1] : null; }

  function build(src, scope, handlers, out) {
    var kids = src.childNodes;
    for (var i = 0; i < kids.length; i++) {
      var n = kids[i];
      if (n.nodeType === 3) { out.appendChild(document.createTextNode(interp(n.nodeValue, scope))); continue; }
      if (n.nodeType !== 1) continue;
      var tag = n.tagName.toLowerCase();
      if (tag === "sc-for") {
        var list = lookup(scope, exprOf(n.getAttribute("list")) || "") || [];
        var as = n.getAttribute("as") || "item";
        for (var j = 0; j < list.length; j++) {
          var sub = Object.assign({}, scope); sub[as] = list[j];
          build(n, sub, handlers, out);
        }
        continue;
      }
      if (tag === "sc-if") {
        if (lookup(scope, exprOf(n.getAttribute("value")) || "")) build(n, scope, handlers, out);
        continue;
      }
      var el = document.createElementNS(n.namespaceURI, n.localName);
      for (var a = 0; a < n.attributes.length; a++) {
        var at = n.attributes[a];
        if (/^hint-/.test(at.name)) continue;
        if (/^on/i.test(at.name) && exprOf(at.value)) {
          var fn = lookup(scope, exprOf(at.value));
          if (typeof fn === "function") el.setAttribute("data-dc-" + at.name.slice(2).toLowerCase(), handlers.push(fn) - 1);
          continue;
        }
        el.setAttribute(at.name, interp(at.value, scope));
      }
      if (tag === "input" && el.hasAttribute("value")) el.value = el.getAttribute("value");
      build(n, scope, handlers, el);
      out.appendChild(el);
    }
  }

  function DCLogic(props) { this.props = props || {}; this.state = {}; }
  DCLogic.prototype.setState = function (patch) {
    Object.assign(this.state, patch || {});
    if (this.__schedule) this.__schedule();
  };

  function mount(Component, root, tpl, props) {
    var comp = new Component(props);
    comp.props = props || {};
    comp.state = comp.state || {};
    var handlers = [];
    var queued = false;
    function render() {
      queued = false;
      var next = [];
      var frag = document.createElement("div");
      build(tpl.content, comp.renderVals(), next, frag);
      window.morphdom(root, frag, {
        childrenOnly: true,
        onBeforeElUpdated: function (from, to) {
          if (from === document.activeElement && (from.tagName === "INPUT" || from.tagName === "TEXTAREA")) to.value = from.value;
          return !from.isEqualNode(to);
        }
      });
      handlers = next;
    }
    comp.__schedule = function () { if (!queued) { queued = true; Promise.resolve().then(render); } };
    ["click", "input", "submit", "change"].forEach(function (type) {
      root.addEventListener(type, function (ev) {
        var t = ev.target && ev.target.closest ? ev.target.closest("[data-dc-" + type + "]") : null;
        if (!t || !root.contains(t)) return;
        var fn = handlers[Number(t.getAttribute("data-dc-" + type))];
        if (type === "submit") ev.preventDefault();
        if (fn) fn(ev);
      });
    });
    render();
    if (comp.componentDidMount) comp.componentDidMount();
    window.addEventListener("pagehide", function () { if (comp.componentWillUnmount) comp.componentWillUnmount(); });
    return comp;
  }

  window.DCLogic = DCLogic;
  window.dcLite = { mount: mount, _build: build };
})();
