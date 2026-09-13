import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
export default defineConfig({plugins:[react(),tailwindcss()],resolve:{alias:{'@':path.resolve(import.meta.dirname,'src')}},server:{allowedHosts:true},build:{rollupOptions:{output:{manualChunks:{'world-data':['world-atlas/countries-110m.json'],'animation':['motion/react']}}}}});
