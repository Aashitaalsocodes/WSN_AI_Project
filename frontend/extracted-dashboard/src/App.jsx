import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AnimatePresence, motion } from 'framer-motion';
import Sidebar from './components/Sidebar';
import Ticker from './components/Ticker';
import NetworkOverview from './pages/NetworkOverview';
import AttackDetection from './pages/AttackDetection';
import RoutingSimulation from './pages/RoutingSimulation';
import EnergyForecast from './pages/EnergyForecast';
import PipelineReport from './pages/PipelineReport';

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.25, ease: 'easeIn' } },
};

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageWrap><NetworkOverview /></PageWrap>} />
        <Route path="/attack-detection" element={<PageWrap><AttackDetection /></PageWrap>} />
        <Route path="/routing" element={<PageWrap><RoutingSimulation /></PageWrap>} />
        <Route path="/energy" element={<PageWrap><EnergyForecast /></PageWrap>} />
        <Route path="/report" element={<PageWrap><PipelineReport /></PageWrap>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

function PageWrap({ children }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {children}
    </motion.div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-dashboard transition-colors duration-300">
          <Sidebar />
          <main className="pt-14 pb-12 lg:ml-64 lg:pt-0">
            <div className="min-h-screen p-4 md:p-6 lg:p-8">
              <AnimatedRoutes />
            </div>
          </main>
          <Ticker />
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}
