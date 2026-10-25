const colors = {
  bg: "#F5F6F2",
  surface: "#FFFFFF",
  raised: "#EDF1EC",
  panel: "#FFF6E6",
  text: "#1C2925",
  body: "#52615B",
  pale: "#34443D",
  teal: "#126B59",
  tealText: "#FFFFFF",
  amber: "#714400",
  amberBody: "#55452C",
  danger: "#B53E3E",
  outline: "#7F9186",
};
function channel(value) {
  const c = parseInt(value, 16) / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}
function luminance(hex) {
  const rgb = hex.slice(1);
  return 0.2126 * channel(rgb.slice(0, 2)) + 0.7152 * channel(rgb.slice(2, 4)) + 0.0722 * channel(rgb.slice(4, 6));
}
function ratio(a, b) {
  const values = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (values[0] + 0.05) / (values[1] + 0.05);
}
const textPairs = [
  ["body on bg", "body", "bg"], ["body on surface", "body", "surface"], ["body on raised", "body", "raised"],
  ["primary on bg", "text", "bg"], ["primary on surface", "text", "surface"], ["primary on raised", "text", "raised"],
  ["pale on bg", "pale", "bg"], ["pale on surface", "pale", "surface"],
  ["teal link on bg", "teal", "bg"], ["teal link on surface", "teal", "surface"], ["teal link on raised", "teal", "raised"],
  ["button text on teal", "tealText", "teal"], ["amber on warning panel", "amber", "panel"],
  ["warning body on panel", "amberBody", "panel"], ["danger on bg", "danger", "bg"],
  ["danger on surface", "danger", "surface"], ["danger on raised", "danger", "raised"],
];
let failed = false;
for (const [label, fg, bg] of textPairs) {
  const value = ratio(colors[fg], colors[bg]);
  const pass = value >= 4.5;
  console.log((pass ? "PASS " : "FAIL ") + label + ": " + value.toFixed(2) + ":1 (4.5:1 required)");
  if (!pass) failed = true;
}
const uiPairs = [
  ["input outline on bg", "outline", "bg"],
  ["input outline on surface", "outline", "surface"],
  ["focus teal on bg", "teal", "bg"],
  ["focus teal on surface", "teal", "surface"],
];
for (const [label, fg, bg] of uiPairs) {
  const value = ratio(colors[fg], colors[bg]);
  const pass = value >= 3;
  console.log((pass ? "PASS " : "FAIL ") + label + ": " + value.toFixed(2) + ":1 (3:1 required)");
  if (!pass) failed = true;
}
if (failed) process.exitCode = 1;
