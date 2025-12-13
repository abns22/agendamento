import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './features/admin-dashboard/AuthProvider'
import MobileLayout from './components/MobileLayout'
import BookingWizard from './features/public-booking/BookingWizard'
import Home from './pages/Home'
import LoginPage from './features/admin-dashboard/LoginPage'
import DashboardPage from './features/admin-dashboard/DashboardPage'
import DashboardLayout from './features/admin-dashboard/DashboardLayout'
import ProtectedRoute from './features/admin-dashboard/ProtectedRoute'
import ServicesPage from './features/admin-dashboard/ServicesPage'
import AgendaPage from './features/admin-dashboard/AgendaPage'
import BillingPage from './features/admin-dashboard/BillingPage'
import SettingsPage from './features/admin-dashboard/SettingsPage'
import CaixaPage from './features/admin-dashboard/CaixaPage'
import DebtorsPage from './features/admin-dashboard/DebtorsPage'
import InventoryPage from './features/admin-dashboard/InventoryPage'
import ProductsPage from './features/admin-dashboard/ProductsPage'
import SuperAdminPage from './features/admin-dashboard/SuperAdminPage'

function App() {
  // Debug: Log quando o componente renderiza
  console.log('🚀 App renderizado, pathname:', window.location.pathname)

  return (
    <AuthProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          {/* Redirecionar rota raiz para /admin/login */}
          <Route path="/" element={<Navigate to="/admin/login" replace />} />
          
          {/* Rotas Públicas */}
          {/* Rota principal de agendamento */}
          <Route 
            path="/booking/:tenantSlug" 
            element={
              <MobileLayout>
                <BookingWizard />
              </MobileLayout>
            } 
          />
          {/* Rota alternativa /book/:tenantSlug (compatibilidade) - redireciona para /booking/:tenantSlug */}
          <Route 
            path="/book/:tenantSlug" 
            element={
              <MobileLayout>
                <BookingWizard />
              </MobileLayout>
            } 
          />
          
          {/* Rotas de Autenticação - DEVE VIR ANTES de /admin/* */}
          {/* Redirecionar /login/admin para /admin/login (compatibilidade) */}
          <Route path="/login/admin" element={<Navigate to="/admin/login" replace />} />
          <Route path="/admin/login" element={<LoginPage />} />
          
          {/* Rotas Protegidas (Admin) - Usando DashboardLayout */}
          <Route
            path="/admin/*"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Routes>
                    <Route path="dashboard" element={<DashboardPage />} />
                    <Route path="agenda" element={<AgendaPage />} />
                    <Route path="servicos" element={<ServicesPage />} />
                    <Route path="configuracoes" element={<SettingsPage />} />
                    <Route path="billing" element={<BillingPage />} />
                    <Route path="billing/success" element={<BillingPage />} />
                    <Route path="caixa" element={<CaixaPage />} />
                    <Route path="devedores" element={<DebtorsPage />} />
                    <Route path="inventario" element={<InventoryPage />} />
                    <Route path="produtos" element={<ProductsPage />} />
                    <Route path="super-admin" element={<SuperAdminPage />} />
                    <Route path="" element={<DashboardPage />} />
                  </Routes>
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          
          {/* Rota padrão - Deve ser a última */}
          <Route path="*" element={<MobileLayout><Home /></MobileLayout>} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App


