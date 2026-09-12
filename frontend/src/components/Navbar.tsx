import React from "react";
import { LayoutGrid, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface NavbarProps {
  onGoToDashboard?: () => void;
  title?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ onGoToDashboard, title }) => {
  const { user, logout } = useAuth();

  return (
    <header className="h-14 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between select-none z-30">
      <div className="flex items-center space-x-4">
        <button
          onClick={onGoToDashboard}
          className="flex items-center space-x-2 text-indigo-400 hover:text-indigo-300 font-bold text-lg cursor-pointer focus:outline-none transition-colors"
        >
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
            <LayoutGrid className="w-5 h-5" />
          </div>
          <span className="tracking-tight text-white font-semibold">Kanvaset</span>
        </button>

        {title && (
          <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
            <span>/</span>
            <span className="text-slate-200 font-medium truncate max-w-xs">{title}</span>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4">
        {user && (
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
              <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold uppercase text-[10px]">
                {user.username.charAt(0)}
              </div>
              <span className="font-medium text-slate-200">{user.username}</span>
            </div>

            <button
              onClick={logout}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
