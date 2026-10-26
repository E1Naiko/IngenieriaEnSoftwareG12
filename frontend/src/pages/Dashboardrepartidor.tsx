import { Navigate, useNavigate } from "react-router-dom";

function DashboardRepartidor() {
  const navigate = useNavigate();
  const guardado = localStorage.getItem("repartidor");

  // Si no hay sesión iniciada, vuelve al login
  if (!guardado) return <Navigate to="/" replace />;

  const repartidor = JSON.parse(guardado);

  function cerrarSesion() {
    localStorage.removeItem("repartidor");
    navigate("/");
  }

  return (
    <div>
      <h1>Panel de paquetes</h1>
      <p>Bienvenido, {repartidor.nombre}. Iniciaste sesión correctamente.</p>
      <button type="button" onClick={cerrarSesion}>
        Cerrar sesión
      </button>
    </div>
  );
}

export default DashboardRepartidor;