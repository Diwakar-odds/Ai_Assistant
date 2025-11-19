import { Home, LayoutDashboard, Grid3x3, Mic, MessageSquare, Settings, LogOut, User } from 'lucide-react';

interface SidebarProps {
  activeSection: string;
  setActiveSection: (section: string) => void;
  username?: string | null;
  onLogout?: () => void;
}

const Sidebar = ({ activeSection, setActiveSection, username, onLogout }: SidebarProps) => {
  const menuItems = [
    { id: 'command', icon: Home, label: 'Command' },
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'apps', icon: Grid3x3, label: 'Apps' },
    { id: 'voice', icon: Mic, label: 'Voice' },
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-20 glass-strong z-50 flex flex-col items-center py-8">
      <div className="mb-12 relative">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#00CEC9] to-[#6C5CE7] flex items-center justify-center animate-breathe">
          <span className="text-2xl font-bold">YD</span>
        </div>
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-[#00B894] rounded-full animate-pulse"></div>
      </div>

      <nav className="flex-1 flex flex-col gap-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`relative w-14 h-14 rounded-xl flex items-center justify-center transition-all duration-300 group ${
                isActive
                  ? 'bg-gradient-to-br from-[#00CEC9] to-[#6C5CE7] shadow-lg shadow-[#00CEC9]/50'
                  : 'hover:bg-white/10'
              }`}
              title={item.label}
            >
              <Icon size={24} className={`transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
              {isActive && (
                <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#00CEC9] rounded-r-full"></div>
              )}
              <div className="absolute left-20 bg-black/90 text-white px-3 py-2 rounded-lg text-sm opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
                {item.label}
              </div>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        {/* User profile with tooltip showing username */}
        <div className="relative group">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#6C5CE7] to-[#E17055] cursor-pointer hover:scale-110 transition-transform flex items-center justify-center">
            {username ? (
              <span className="text-white font-bold text-lg">{username[0].toUpperCase()}</span>
            ) : (
              <User className="w-5 h-5 text-white" />
            )}
          </div>
          {username && (
            <div className="absolute left-20 bottom-0 bg-black/90 text-white px-3 py-2 rounded-lg text-sm opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
              {username}
            </div>
          )}
        </div>

        {/* Logout button */}
        {onLogout && (
          <button
            onClick={onLogout}
            className="w-10 h-10 rounded-full bg-red-500/20 hover:bg-red-500/30 transition-all duration-300 flex items-center justify-center group relative"
            title="Logout"
          >
            <LogOut className="w-5 h-5 text-red-400" />
            <div className="absolute left-20 bottom-0 bg-black/90 text-white px-3 py-2 rounded-lg text-sm opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
              Logout
            </div>
          </button>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
