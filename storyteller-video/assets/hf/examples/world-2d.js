// Example world (2D): a pipeline of stations joined by a belt, with one token (the protagonist) on it.
// Replace the set with the video's own world; keep the contract: views, build, objects. See references/world.md.
(function () {
  const STATIONS = [
    { id: "input", x: 360, label: "Input" },
    { id: "model", x: 960, label: "Model" },
    { id: "output", x: 1560, label: "Output" },
  ];
  const BELT_Y = 600;
  window.WORLD = {
    // the frame centre looks at (x, y) at zoom; one wide view and one close view per idea the story visits
    views: {
      wide: { x: 960, y: 560, zoom: 1 },
      "close-model": { x: 960, y: 560, zoom: 2.2 },
      "close-output": { x: 1560, y: 560, zoom: 2.2 },
    },
    objects: {},
    build(layer) {
      const o = this.objects;
      o.belt = el("div", "abs", layer, { left: "240px", top: BELT_Y + "px", width: "1440px", height: "12px", borderRadius: "6px", background: "var(--line)" });
      STATIONS.forEach((s) => {
        const box = el("div", "abs", layer, { left: s.x - 150 + "px", top: BELT_Y - 260 + "px", width: "300px", height: "220px", borderRadius: "16px", background: "var(--surface)" });
        el("div", "abs t-h2", box, { left: 0, top: "80px", width: "300px", textAlign: "center", color: "var(--ink)" }, s.label);
        o[s.id] = box;
      });
      // the protagonist: scene modules move it along the belt with tweens on tl
      o.token = el("div", "abs", layer, { left: "330px", top: BELT_Y - 24 + "px", width: "60px", height: "60px", borderRadius: "50%", background: "var(--accent)" });
    },
  };
})();
