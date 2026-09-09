import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('smartinvoice_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('smartinvoice_token') || null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('smartinvoice_token');
      if (storedToken) {
        try {
          const userData = await authService.getMe();
          setUser(userData);
          localStorage.setItem('smartinvoice_user', JSON.stringify(userData));
        } catch (error) {
          console.error('Failed to validate session token:', error);
          logout();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const data = await authService.login(email, password);
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('smartinvoice_token', data.access_token);
    localStorage.setItem('smartinvoice_user', JSON.stringify(data.user));
    return data;
  };

  const register = async (userData) => {
    const data = await authService.register(userData);
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('smartinvoice_token', data.access_token);
    localStorage.setItem('smartinvoice_user', JSON.stringify(data.user));
    return data;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('smartinvoice_token');
    localStorage.removeItem('smartinvoice_user');
  };

  const hasRole = (allowedRoles) => {
    if (!user || !user.role) return false;
    if (Array.isArray(allowedRoles)) {
      return allowedRoles.includes(user.role);
    }
    return user.role === allowedRoles;
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    register,
    logout,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
