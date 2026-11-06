# React + TypeScript + Vite

## Scripts y despliegue

```bash
npm install     # o npm ci, que es lo que usa Vercel
npm run dev     # servidor de desarrollo en http://localhost:5173
npm run build   # tsc -b && vite build → genera dist/ (esto es lo que Vercel necesita)
npm run preview # sirve dist/ localmente para probar el build de producción
npm run lint    # oxlint
```

En desarrollo, los pedidos a `/api/*` los proxifica Vite al backend Django
(`server.proxy` en `vite.config.ts`, por defecto `http://127.0.0.1:8000`,
cambiable con la variable de entorno `VITE_BACKEND_URL`). Por eso el código
usa **rutas relativas**: no escribir `http://127.0.0.1:8000/...` en los
`fetch`, porque en producción eso apunta a la máquina del visitante y rompe la
cookie de sesión al volverse cross-origin.

En producción (Vercel) la configuración está en `vercel.json`: build
`npm run build`, salida `dist`, un rewrite de `/api/:path*` al backend en Render
(`https://ingenieriaensoftwareg12.onrender.com`) y un rewrite del resto a
`/index.html` para las rutas de React Router. El detalle y los pasos del deploy
están en el
[README del repositorio](../README.md#despliegue-del-frontend-en-vercel).

---

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
