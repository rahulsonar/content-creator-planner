"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { clearAuth } from "@/lib/auth/helpers";

export default function LogoutButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleLogout = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include', // Ensure cookies are sent
      });
      
      if (!response.ok) {
        throw new Error('Logout failed');
      }
      
      // Clear localStorage using helper
      clearAuth();
      
      // Redirect to login
      router.push('/login');
      router.refresh(); // Force refresh to clear any cached data
    } catch (error) {
      console.error('Logout error:', error);
      // Clear auth anyway and redirect
      clearAuth();
      router.push('/login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleLogout}
      disabled={loading}
      className={className}
    >
      {loading ? 'Logging out...' : 'Logout'}
    </button>
  );
}
