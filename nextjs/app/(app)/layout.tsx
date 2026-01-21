import Link from "next/link";
import LogoutButton from "@/app/components/LogoutButton";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <nav className="bg-gray-800 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex space-x-8">
              <Link href="/" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Home
              </Link>
              <Link href="/kanban" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Board
              </Link>
              <Link href="/calendar" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Calendar
              </Link>
              <Link href="/chat" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                AI Chat
              </Link>
              <Link href="/conversations" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Conversations
              </Link>
              <Link href="/agent-logs" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Agent Logs
              </Link>
            </div>
            <div>
              <LogoutButton />
            </div>
          </div>
        </div>
      </nav>
      <main>{children}</main>
    </>
  );
}
