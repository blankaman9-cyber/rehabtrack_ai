const ArrowUpRight = ({ className = "h-4 w-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 17L17 7M7 7h10v10" />
  </svg>
);

const Navbar = ({ role, user, onSwitchRole }) => {
  return (
    <nav className="fixed top-4 left-0 right-0 px-8 lg:px-16 z-50 flex items-center justify-between pointer-events-none">
      {/* Left: Spacer to keep branding centered */}
      <div className="w-12 h-12" />

      {/* Center: Branding */}
      <div className="flex items-center gap-3 liquid-glass rounded-full px-5 py-2 pointer-events-auto">
        <span className="font-heading italic text-xl text-white tracking-wide">
          RehabTrack
        </span>
        <span className="w-1 h-1 bg-white/20 rounded-full" />
        <span className="text-xs uppercase tracking-widest text-white/50 font-body font-medium">
          {role ? (user ? `${role} portal: ${user.name}` : `${role} portal`) : "Select Portal"}
        </span>
      </div>

      {/* Right: Sign Out or actions */}
      <div className="pointer-events-auto">
        {role && (
          <button
            onClick={onSwitchRole}
            className="liquid-glass rounded-full px-4 py-2 text-sm font-medium text-white/90 hover:text-white flex items-center gap-2 hover:bg-white/5 transition-all"
          >
            Sign Out
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        )}
      </div>
    </nav>
  );
};

window.Navbar = Navbar;
window.ArrowUpRight = ArrowUpRight;
