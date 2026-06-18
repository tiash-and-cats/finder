import sharp from "sharp";
import figlet from "figlet";
import colors from "ansi-colors";
import fs from "fs/promises";
import { pastel } from 'gradient-string';

async function convertToAscii(imagePath, targetWidth = 80) {
  // Fetch metadata first to calculate a proportional height
  const metadata = await sharp(imagePath).metadata();
  
  // Terminal characters are tall. To keep a 1:1 pixel aspect ratio 
  // using half-blocks, we need exactly 2 vertical pixels per row.
  const aspect = metadata.height / metadata.width;
  const targetHeight = Math.round(targetWidth * aspect);
  
  // Ensure height is an even number so every block has a top and bottom pixel
  const finalHeight = targetHeight % 2 === 0 ? targetHeight : targetHeight + 1;

  // Extract raw RGB data (3 channels: Red, Green, Blue)
  const { data, info } = await sharp(imagePath)
    .resize({ width: targetWidth, height: finalHeight, fit: 'fill' })
    .raw() 
    .toBuffer({ resolveWithObject: true });

  const imgAscii = [];
  const bytesPerPixel = 4; // RGBA
  const rowStride = info.width * bytesPerPixel;

  // Loop through rows TWO at a time (Y steps by 2)
  for (let y = 0; y < info.height; y += 2) {
    let currentRow = "";
    for (let x = 0; x < info.width; x++) {
      
      // Calculate buffer offsets for top and bottom pixels
      const topIdx = (y * rowStride) + (x * bytesPerPixel);
      const btmIdx = ((y + 1) * rowStride) + (x * bytesPerPixel);

      // Extract RGBA values
      const rTop = data[topIdx];
      const gTop = data[topIdx + 1];
      const bTop = data[topIdx + 2];
      const aTop = data[topIdx + 3];

      const rBtm = data[btmIdx];
      const gBtm = data[btmIdx + 1];
      const bBtm = data[btmIdx + 2];
      const aBtm = data[btmIdx + 3];

      // Construct Truecolor ANSI Escape Sequences:
      // \x1b[48;2;R;G;Bm sets BACKGROUND color (Top pixel)
      // \x1b[38;2;R;G;Bm sets FOREGROUND color (Bottom pixel)
      currentRow += (aTop >= 1.5 ? `\x1b[48;2;${rTop};${gTop};${bTop}m` : `\x1b[40m`) +
                    (aBtm >= 1.5 ? `\x1b[38;2;${rBtm};${gBtm};${bBtm}m` : `\x1b[30m`) + "▄";
    }
    
    // Reset formatting at the end of the line and append to full art
    imgAscii.push(currentRow + "\x1b[0m");
  }

  return imgAscii;
}

const LOGO_WIDTH = 21;

const logoImgAscii = await convertToAscii('logo.svg', LOGO_WIDTH);

let logoTextAscii = await figlet.text("find4u CLI", { font: "Slant" });
logoTextAscii = pastel.multiline(logoTextAscii);
logoTextAscii = logoTextAscii.split("\n");

let infoAscii = [
  `Hello, I'm Find4U, your personal ${colors.bold.underline("coding assistant")}`,
  colors.bold.italic("Got a question? I'll jump in."), "",
  colors.bold.magenta("See the docs at https://finder-locw.onrender.com/docs/dev/find4u-cli/"),
  `${colors.dim.italic("Type")} ${colors.cyan("/exit")} ${colors.dim.italic("to exit.")}`
];

const asciiArt = logoImgAscii;

let i = 0, j = 0;
for (; i < logoTextAscii.length; i++) {
  asciiArt[i] = (asciiArt[i] || " ".repeat(LOGO_WIDTH)) + "  " + logoTextAscii[i];
}
j = i;
for (; (i - j) < infoAscii.length; i++) {
  asciiArt[i] = (asciiArt[i] || " ".repeat(LOGO_WIDTH)) + "  " + infoAscii[i - j];
}

console.log(asciiArt.join("\n"));
await fs.writeFile("splash.json", JSON.stringify(asciiArt));
console.log("Wrote to splash.json");