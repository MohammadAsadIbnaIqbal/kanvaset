import React, { useState } from "react";
import { AuthPage } from "./components/Auth/AuthPage";
import { BoardPage } from "./components/Board/BoardPage";
import { DashboardPage } from "./components/Dashboard/DashboardPage";
import { Navbar } from "./components/Navbar";
import { AuthProvider, useAuth } from "./context/AuthContext";

const MainApp: React.FC = () => {
  const { user, loading } = useAuth();
  const [activeBoardId, setActiveBoardId] = useState<string | null>(() => {
    if (typeof window !== "undefined" && window.location.hash.startsWith("#board=")) {
      return window.location.hash.replace("#board=", "");
    }
    return null;
  });

  const handleSelectBoard = (boardId: string | null) => {
    setActiveBoardId(boardId);
    if (typeof window !== "undefined") {
      if (boardId) {
        window.location.hash = `board=${boardId}`;
      } else {
        history.pushState("", document.title, window.location.pathname + window.location.search);
      }
    }
  };

  React.useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash.startsWith("#board=")) {
        setActiveBoardId(window.location.hash.replace("#board=", ""));
      } else {
        setActiveBoardId(null);
      }
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

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

  if (activeBoardId) {
    return (
      <BoardPage
        boardId={activeBoardId}
        onBack={() => handleSelectBoard(null)}
      />
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 overflow-hidden">
      <Navbar />
      <DashboardPage onSelectBoard={(boardId) => handleSelectBoard(boardId)} />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
