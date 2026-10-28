import { Link } from "react-router-dom";

function Dashboard() {
  return (
    <div style={{ padding: "1rem" }}>
      <h1>Bienvenido al Dashboard</h1>
      <p>Iniciaste sesión correctamente.</p>
      <p>
        <Link to="/comercios">Gestionar comercios</Link>
        <br></br>
        <Link to="/flota">Ver Flota Disponible</Link>
      </p>
      <p>
        <Link to="/ingresar-pedido">Ingresar pedido</Link>
      </p>
    </div>
  );
}

export default Dashboard;
