
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import "./login.css";

function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  
  const navigate = useNavigate();
  
  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/login/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Error al iniciar sesión");
      }
      navigate("/dashboard");
      setLoggedIn(true);
      setMessage(data.message);
    } catch (error) {
      setLoggedIn(false);

      if (error instanceof Error) {
        setMessage(error.message);
      } else {
        setMessage("No se pudo conectar con el servidor");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-container">
      <form className="login-card" onSubmit={handleLogin}>
        <h1>{loggedIn ? "¡Bienvenido!" : "Iniciar sesión"}</h1>

        {loggedIn ? (
          <>
            <p>{message}</p>
            <button
              type="button"
              onClick={() => {
                setLoggedIn(false);
                setUsername("");
                setPassword("");
                setMessage("");
              }}
            >
              Cerrar sesión
            </button>
          </>
        ) : (
          <>
            <label htmlFor="username">Usuario</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Ingresá tu usuario"
              required
            />

            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Ingresá tu contraseña"
              required
            />

            <button type="submit" disabled={loading}>
              {loading ? "Conectando..." : "Ingresar"}
            </button>

            {message && <p className="error-message">{message}</p>}
          </>
        )}
      </form>
    </main>
  );
}

export default Login;
