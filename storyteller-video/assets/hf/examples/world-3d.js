// Example world (3D, Three.js): a field of bars on a plane, seen by an orbiting camera.
// Use 3D when depth carries meaning (a pull-out over many units, a surface, a stack). Seek-safe: render() draws
// one frame from the time and the camera; nothing animates on its own. See references/world.md.
(function () {
  let renderer, scene, camera;
  const GRID = 5, GAP = 8;
  window.WORLD = {
    // camera keys are this world's own: azimuth, elevation (radians) and distance from the centre
    views: { wide: { az: 0.6, el: 0.55, dist: 64 }, close: { az: 1.5, el: 0.25, dist: 22 } },
    objects: {},
    build(layer, ctx) {
      Object.assign(ctx.CAM, this.views.wide);
      const canvas = el("canvas", "abs", layer, { left: 0, top: 0, width: "1920px", height: "1080px" });
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
      renderer.setSize(1920, 1080, false);
      renderer.setClearColor(0x000000, 0); // clear: the world layer paints the beat's ground behind the canvas
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(35, 1920 / 1080, 0.1, 500);
      scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.0));
      const sun = new THREE.DirectionalLight(0xffffff, 0.6);
      sun.position.set(20, 40, 10);
      scene.add(sun);
      const roles = [C.orange, C.blue, C.teal, C.purple];
      for (let i = 0; i < GRID * GRID; i++) {
        const h = 2 + ((i * 7) % 9); // a fixed pattern, never Math.random: a seek must draw the same frame
        const bar = new THREE.Mesh(new THREE.BoxGeometry(4, h, 4), new THREE.MeshLambertMaterial({ color: new THREE.Color(roles[i % 4]) }));
        bar.position.set(((i % GRID) - 2) * GAP, h / 2, (Math.floor(i / GRID) - 2) * GAP);
        scene.add(bar);
        this.objects["bar" + i] = bar; // a module may tween bar.scale.y or bar.position on tl
      }
    },
    render(t, cam) {
      camera.position.set(cam.dist * Math.cos(cam.el) * Math.sin(cam.az), cam.dist * Math.sin(cam.el), cam.dist * Math.cos(cam.el) * Math.cos(cam.az));
      camera.lookAt(0, 2, 0);
      renderer.render(scene, camera);
    },
  };
})();
