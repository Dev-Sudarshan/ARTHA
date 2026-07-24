import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar/Navbar';

// Eagerly load Home (landing page)
import Home from './pages/Home/Home';

// Lazy load all other pages — only downloaded when visited
const Marketplace = lazy(() => import('./pages/Marketplace/Marketplace'));
const Portfolio = lazy(() => import('./pages/Portfolio/Portfolio'));
const Login = lazy(() => import('./pages/Login/Login'));
const ForgotPassword = lazy(() => import('./pages/Login/ForgotPassword'));
const Signup = lazy(() => import('./pages/Signup/Signup'));
const Profile = lazy(() => import('./pages/Profile/Profile'));
const KYC = lazy(() => import('./pages/KYC/KYC'));
const LoanRequest = lazy(() => import('./pages/LoanRequest/LoanRequest'));
const Payment = lazy(() => import('./pages/Payment/Payment'));
const BankConnectionDemo = lazy(() => import('./pages/BankConnectionDemo/BankConnectionDemo'));

const PageLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
    <div className="text-muted">Loading...</div>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <Navbar />
          <div className="content">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/marketplace" element={<Marketplace />} />
                <Route path="/portfolio" element={<Portfolio />} />
                <Route path="/login" element={<Login />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/kyc" element={<KYC />} />
                <Route path="/request-loan" element={<LoanRequest />} />
                <Route path="/payment" element={<Payment />} />
                <Route path="/bank-connection-demo" element={<BankConnectionDemo />} />
              </Routes>
            </Suspense>
          </div>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
