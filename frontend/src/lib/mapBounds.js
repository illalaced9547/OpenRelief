export const WORLD_WIDTH = 1040;
// Wrap longitude endlessly; allow 42 screen units of vertical breathing room.
export function clampMapCenter([x,y], zoom) {
 const z=Math.max(1,Math.min(10,zoom));
 const verticalLimit=270*(1-1/z)+42/z;
 return [((x%WORLD_WIDTH)+WORLD_WIDTH)%WORLD_WIDTH,
  Math.max(270-verticalLimit,Math.min(270+verticalLimit,y))];
}
