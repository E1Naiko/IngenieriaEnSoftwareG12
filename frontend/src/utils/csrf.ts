// Token CSRF para las peticiones que modifican datos con la sesión del
// coordinador (Django lo exige en POST/PUT/PATCH/DELETE).
//
// Cómo funciona:
//   1. El navegador guarda la cookie `csrftoken`; Django la crea al iniciar
//      sesión (POST /api/login-coordinador/) y también con cada request.
//   2. El front la lee de `document.cookie` y la manda en el header
//      `X-CSRFToken`, que es el nombre que espera Django.
//
// La cookie es del mismo origen porque las rutas son relativas (/api/...) y
// en desarrollo las proxifica Vite: en ese caso `document.cookie` la ve.
// Si algún día el front llama a otro dominio, ese dominio tiene que estar en
// CSRF_TRUSTED_ORIGINS y la petición necesita `credentials: "include"`.

const NOMBRE_COOKIE = "csrftoken";

/** Lee una cookie por nombre. Devuelve "" si no existe. */
function leerCookie(nombre: string): string {
  const prefijo = `${nombre}=`;
  const partes = document.cookie ? document.cookie.split(";") : [];

  for (const parte of partes) {
    const valor = parte.trim();
    if (valor.startsWith(prefijo)) {
      return decodeURIComponent(valor.slice(prefijo.length));
    }
  }

  return "";
}

/**
 * Archivo de headers para una petición que modifica datos.
 *
 * Uso:
 *   fetch(url, { method: "POST", headers: headersConCsrf(), ... })
 *
 * Si la cookie todavía no existe (por ejemplo, alguien entró directo a la
 * página sin pasar por el login), el header viaja vacío y Django responde 403;
 * el llamador muestra el error.
 */
export function headersConCsrf(): Record<string, string> {
  const token = leerCookie(NOMBRE_COOKIE);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["X-CSRFToken"] = token;
  }

  return headers;
}
