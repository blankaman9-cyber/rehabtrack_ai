const ArrowUpRight = ({ className = "h-4 w-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 17L17 7M7 7h10v10" />
  </svg>
);

const Navbar = () => {
  return (
    <nav className="fixed top-4 left-0 right-0 px-8 lg:px-16 z-50 flex items-center justify-between pointer-events-none">
      {/* Left: 48x48 liquid-glass circle with italic serif lowercase "a" */}
      <div className="w-12 h-12 rounded-full liquid-glass flex items-center justify-center font-heading italic text-2xl text-white pointer-events-auto">
        a
      </div>

      {/* Center (desktop only): liquid-glass pill, px-1.5 py-1.5 */}
      <div className="hidden md:flex items-center gap-1 liquid-glass rounded-full px-1.5 py-1.5 pointer-events-auto">
        {["Home", "Voyages", "Worlds", "Innovation", "Plan Launch"].map((link) => (
          <a
            href={`#${link.toLowerCase().replace(" ", "-")}`}
            key={link}
            className="px-3 py-2 text-sm font-medium text-white/90 font-body hover:text-white transition-colors"
          >
            {link}
          </a>
        ))}
        <button className="bg-white text-black rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap flex items-center gap-1 hover:bg-white/90 transition-colors ml-2">
          Claim a Spot
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>

      {/* Right: 48x48 invisible spacer to balance logo */}
      <div className="w-12 h-12 invisible" />
    </nav>
  );
};

window.Navbar = Navbar;
window.ArrowUpRight = ArrowUpRight;
