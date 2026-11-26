// ビルド: node build.mjs → dist/crash-tools.min.js（CSSは文字列としてJSに埋め込む）
// node build.mjs --dev → minify なし（dist/crash-tools.js）
import { build, transform } from 'esbuild';
import { readFileSync } from 'node:fs';

const dev = process.argv.includes('--dev');
const { version } = JSON.parse(readFileSync('package.json', 'utf8'));

await build({
  entryPoints: ['src/main.js'],
  bundle: true,
  format: 'iife',
  target: ['es2019'],
  minify: !dev,
  charset: 'utf8',
  legalComments: 'none',
  plugins: [{
    name: 'css-text',
    setup(b) {
      b.onLoad({ filter: /\.css$/ }, async (a) => {
        const r = await transform(readFileSync(a.path, 'utf8'), { loader: 'css', minify: !dev, target: ['chrome88', 'safari14', 'firefox78'] });
        return { contents: r.code, loader: 'text' };
      });
    },
  }],
  define: { __VERSION__: JSON.stringify(version) },
  banner: { js: '/* crash-tools v' + version + ' https://github.com/madcocoa-coder/stockcrash-tools */' },
  outfile: dev ? 'dist/crash-tools.js' : 'dist/crash-tools.min.js',
});
console.log('built', dev ? 'dist/crash-tools.js' : 'dist/crash-tools.min.js', 'v' + version);
