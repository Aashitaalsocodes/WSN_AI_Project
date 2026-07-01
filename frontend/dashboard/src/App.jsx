import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Sidebar from './components/Sidebar';
import NetworkOverview from './pages/NetworkOverview';
import AttackDetection from './pages/AttackDetection';
import RoutingSimulation from './pages/RoutingSimulation';
import EnergyForecast from './pages/EnergyForecast';
import PipelineReport from './pages/PipelineReport';

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-surface-50 transition-colors duration-300 dark:bg-surface-950">
          <Sidebar />
          <main className="pt-14 lg:ml-64 lg:pt-0">
            <div className="min-h-screen p-4 md:p-6 lg:p-8">
              <Routes>
                <Route path="/" element={<NetworkOverview />} />
                <Route path="/attack-detection" element={<AttackDetection />} />
                <Route path="/routing" element={<RoutingSimulation />} />
                <Route path="/energy" element={<EnergyForecast />} />
                <Route path="/report" element={<PipelineReport />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </main>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}
