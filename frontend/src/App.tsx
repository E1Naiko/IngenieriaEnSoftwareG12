
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./components/login/login";
import Dashboard from "./pages/Dashboard";
import Comercios from "./pages/Comercios";
import LoginRepartidor from "./components/loginRepartidor/LoginRepartidor";
import DashboardRepartidor from "./pages/Dashboardrepartidor";
import PaquetesEnCurso from "./pages/PaquetesEnCurso";
import "./App.css";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/comercios" element={<Comercios />} /> 
        <Route path="/loginrepartidor" element={<LoginRepartidor />} />
        <Route path="/dashboardrepartidor" element={<DashboardRepartidor />} />
        <Route path="/paquetesencurso" element={<PaquetesEnCurso />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
