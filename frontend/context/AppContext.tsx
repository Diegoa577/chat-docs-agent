"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface SnackbarMessage {
  id: string;
  message: string;
  severity: "success" | "info" | "warning" | "error";
}

interface AppContextValue {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  toggleMobileOpen: () => void;
  snackbars: SnackbarMessage[];
  showSnackbar: (message: string, severity?: SnackbarMessage["severity"]) => void;
  closeSnackbar: (id: string) => void;
  sidebar: ReactNode | null;
  setSidebar: (sidebar: ReactNode | null) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [snackbars, setSnackbars] = useState<SnackbarMessage[]>([]);
  const [sidebar, setSidebar] = useState<ReactNode | null>(null);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
      timers.clear();
    };
  }, []);

  const toggleMobileOpen = useCallback(() => {
    setMobileOpen((prev) => !prev);
  }, []);

  const showSnackbar = useCallback(
    (message: string, severity: SnackbarMessage["severity"] = "info") => {
      const id = `${Date.now()}-${Math.random()}`;
      setSnackbars((prev) => [...prev, { id, message, severity }]);
      const timer = setTimeout(() => {
        timersRef.current.delete(id);
        setSnackbars((prev) => prev.filter((s) => s.id !== id));
      }, 6000);
      timersRef.current.set(id, timer);
    },
    []
  );

  const closeSnackbar = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setSnackbars((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return (
    <AppContext.Provider
      value={{
        mobileOpen,
        setMobileOpen,
        toggleMobileOpen,
        snackbars,
        showSnackbar,
        closeSnackbar,
        sidebar,
        setSidebar,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within AppProvider");
  }
  return context;
}
