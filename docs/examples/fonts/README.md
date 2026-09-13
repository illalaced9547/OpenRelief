# Offline typography

The annotation atlas uses the frontend's **Manrope** headings and **DM Sans** body text.
The font files are bundled so the gallery and exported diagrams work without a network
connection. Their SIL Open Font License files are included alongside them.

- Manrope: https://github.com/google/fonts/tree/main/ofl/manrope
- DM Sans: https://github.com/google/fonts/tree/main/ofl/dmsans

`Manrope.ttf` and `DMSans.ttf` are upstream variable fonts. `Manrope-Medium.ttf` (weight 500)
and `DMSans-Regular.ttf` (weight 400, optical size 14) are static instances produced with
fontTools for consistent Matplotlib rendering. The generated pipeline SVG embeds the
static font data; the HTML gallery uses the local variable files.

Visual references: `frontend/src/neutral.css`, `frontend/src/components/Methodology.css`
and the font declarations in `frontend/index.html`. The shared palette is charcoal
`#0b0b0b`, neutral panels `#202020`, text `#e5e5e5`, secondary text `#aaaaaa` and thin
translucent white borders. The historical outcome markers use the frontend's muted
coral, amber and sage colors; they do not represent calibrated risk percentages.
