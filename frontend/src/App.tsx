
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./components/login/login";
import Dashboard from "./pages/Dashboard";
import Comercios from "./pages/Comercios";
import Flota from "./pages/Flota";
import LoginRepartidor from "./components/loginRepartidor/LoginRepartidor";
import DashboardRepartidor from "./pages/Dashboardrepartidor";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/comercios" element={<Comercios />} />
        <Route path="/flota" element={<Flota />} />
        <Route path="/comercios" element={<Comercios />} /> 
        <Route path="/loginrepartidor" element={<LoginRepartidor />} />
        <Route path="/dashboardrepartidor" element={<DashboardRepartidor />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
