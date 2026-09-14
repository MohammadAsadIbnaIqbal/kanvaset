import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from "react-router-dom";
import { AuthPage } from "./components/Auth/AuthPage";
import { BoardPage } from "./components/Board/BoardPage";
import { DashboardPage } from "./components/Dashboard/DashboardPage";
import { Navbar } from "./components/Navbar";
import { ProjectPage } from "./components/Project/ProjectPage";
import { AuthProvider, useAuth } from "./context/AuthContext";

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-950 text-slate-400">
        <div className="flex flex-col items-center space-y-3">
          <span className="w-9 h-9 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
          <span className="text-xs font-medium text-slate-400">Loading Kanvaset...</span>
        </div>
      </div>
    );
  }
  if (!user) {
    return <AuthPage />;
  }
  return <>{children}</>;
};

const BoardRoute = () => {
  const { boardId } = useParams();
  const navigate = useNavigate();
  return <BoardPage boardId={boardId!} onBack={() => navigate("/")} />;
};

const MainApp: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 overflow-hidden">
      <Navbar />
      <DashboardPage 
        onSelectBoard={(boardId) => navigate(`/board/${boardId}`)} 
        onSelectProject={(projectId) => navigate(`/project/${projectId}`)}
      />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ProtectedRoute><MainApp /></ProtectedRoute>} />
          <Route path="/board/:boardId" element={<ProtectedRoute><BoardRoute /></ProtectedRoute>} />
          <Route path="/project/:projectId" element={<ProtectedRoute><ProjectPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
