'use client';

import { useEffect, useState } from 'react';
import { getStoredUser } from '@/lib/auth/client';

export default function UserProfile() {
  const [userName, setUserName] = useState<string | null>(null);

  useEffect(() => {
    const user = getStoredUser();
    if (user?.name) {
      setUserName(user.name);
    } else if (user?.email) {
      // Fallback to email if name is not available
      setUserName(user.email);
    }
  }, []);

  if (!userName) {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      <div className="text-right">
        <p className="text-sm font-medium text-white">{userName}</p>
      </div>
      <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
        <span className="text-white text-sm font-semibold">
          {userName.charAt(0).toUpperCase()}
        </span>
      </div>
    </div>
  );
}
