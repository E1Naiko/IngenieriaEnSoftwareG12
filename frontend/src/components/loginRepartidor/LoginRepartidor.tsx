import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import "../login/login.css"; // reutiliza los estilos del login existente

// Ruta relativa al origen del sitio: en desarrollo la proxifica Vite a Django
// (server.proxy en vite.config.ts) y en producción la proxifica Vercel al
// backend (rewrites en frontend/vercel.json). Con una URL absoluta a
// 127.0.0.1:8000 el pedido apuntaba a la máquina de quien abría el sitio y
// además rompía la cookie de sesión por ser cross-origin.
const API_URL = "/api";

function LoginRepartidor() {
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const tokenLimpio = token.trim();
    if (!tokenLimpio) {
      setMessage("Ingresá tu token");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/login-repartidor/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: tokenLimpio }),
      });

      // Escenario 2: el token no existe
      if (response.status === 404) {
        setMessage("Token inválido");
        return;
      }

      // Escenario 3: el repartidor fue dado de baja
      if (response.status === 403) {
        setMessage(
          "El repartidor no se encuentra habilitado. Comuníquese con el coordinador"
        );
        return;
      }

      if (!response.ok) {
        setMessage("Error del servidor. Intentá de nuevo");
        return;
      }

      // Escenario 1: éxito → guarda al repartidor y va al panel de paquetes
      const repartidor = await response.json();
      localStorage.setItem("repartidor", JSON.stringify(repartidor));
      navigate("/dashboardrepartidor");
    } catch {
      setMessage("No se pudo conectar con el servidor");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-container">
      <form className="login-card" onSubmit={handleLogin}>
        <h1>Ingreso de repartidor</h1>

        <label htmlFor="token">Token</label>
        <input
          id="token"
          type="text"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="Ingresá tu token"
          autoComplete="off"
        />

        <button type="submit" disabled={loading}>
          {loading ? "Conectando..." : "Iniciar sesión"}
        </button>

        {message && (
          <p className="error-message" role="alert">
            {message}
          </p>
        )}
      </form>
    </main>
  );
}

export default LoginRepartidor;