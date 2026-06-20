const ClockIcon = () => (
  <svg className="w-[28px] h-[28px] text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const GlobeIcon = () => (
  <svg className="w-[28px] h-[28px] text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
    <path d="M2 12h20" />
  </svg>
);

const PlayIcon = ({ className = "h-4 w-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <polygon points="6 4 20 12 6 20 6 4" />
  </svg>
);

const Hero = () => {
  const commonTransition = { duration: 0.8, ease: "easeOut" };
  const baseAnimation = {
    initial: { filter: "blur(10px)", opacity: 0, y: 20 },
    animate: { filter: "blur(0px)", opacity: 1, y: 0 }
  };

  return (
    <section id="home" className="relative w-full min-h-screen bg-black overflow-hidden flex flex-col justify-between z-10">
      {/* Background video (120% width/height, top-aligned, centered horizontally) */}
      <FadingVideo
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_080021_d598092b-c4c2-4e53-8e46-94cf9064cd50.mp4"
        className="absolute left-1/2 top-0 -translate-x-1/2 object-cover object-top z-0"
        style={{ width: "120%", height: "120%" }}
      />

      {/* Navbar overlay */}
      <Navbar />

      {/* Hero content */}
      <div className="flex-1 flex flex-col items-center justify-center text-center z-10 pt-36 px-4">
        {/* Badge (delay 0.4s) */}
        <Motion.motion.div
          {...baseAnimation}
          transition={{ ...commonTransition, delay: 0.4 }}
          className="liquid-glass rounded-full flex items-center p-1.5 pr-4 mb-6 select-none"
        >
          <span className="bg-white text-black px-3 py-1 text-xs font-semibold rounded-full mr-3">
            New
          </span>
          <span className="text-sm text-white/90 font-body">
            Maiden Crewed Voyage to Mars Arrives 2026
          </span>
        </Motion.motion.div>

        {/* Headline */}
        <BlurText
          text="Venture Past Our Sky Across the Universe"
          className="text-6xl md:text-7xl lg:text-[5.5rem] font-heading italic text-white leading-[0.8] max-w-2xl justify-center tracking-[-4px] mb-6"
        />

        {/* Subheading (delay 0.8s) */}
        <Motion.motion.p
          {...baseAnimation}
          transition={{ ...commonTransition, delay: 0.8 }}
          className="text-sm md:text-base text-white max-w-2xl font-body font-light leading-tight mb-8"
        >
          Discover the universe in ways once unimaginable. Our pioneering vessels and breakthrough engineering bring deep-space exploration within reach—secure and extraordinary.
        </Motion.motion.p>

        {/* CTAs (delay 1.1s) */}
        <Motion.motion.div
          {...baseAnimation}
          transition={{ ...commonTransition, delay: 1.1 }}
          className="flex items-center gap-6 mb-12"
        >
          <button className="liquid-glass-strong rounded-full px-5 py-2.5 text-sm font-medium text-white flex items-center gap-2 hover:opacity-90 transition-opacity">
            Start Your Voyage
            <ArrowUpRight className="h-5 w-5" />
          </button>
          <a
            href="#liftoff"
            className="text-white hover:text-white/80 transition-colors flex items-center gap-2 text-sm font-medium font-body"
          >
            View Liftoff
            <PlayIcon className="h-4 w-4 fill-current" />
          </a>
        </Motion.motion.div>

        {/* Stats row (delay 1.3s) */}
        <Motion.motion.div
          {...baseAnimation}
          transition={{ ...commonTransition, delay: 1.3 }}
          className="flex flex-wrap justify-center items-stretch gap-4"
        >
          {/* Stat 1 */}
          <div className="liquid-glass p-5 w-[220px] rounded-[1.25rem] flex flex-col items-start text-left">
            <div className="mb-6">
              <ClockIcon />
            </div>
            <div className="mt-auto">
              <div className="font-heading italic text-white text-4xl tracking-[-1px] leading-none">
                34.5 Min
              </div>
              <div className="text-xs text-white/70 font-body font-light mt-2">
                Average Videos Watch Time
              </div>
            </div>
          </div>

          {/* Stat 2 */}
          <div className="liquid-glass p-5 w-[220px] rounded-[1.25rem] flex flex-col items-start text-left">
            <div className="mb-6">
              <GlobeIcon />
            </div>
            <div className="mt-auto">
              <div className="font-heading italic text-white text-4xl tracking-[-1px] leading-none">
                2.8B+
              </div>
              <div className="text-xs text-white/70 font-body font-light mt-2">
                Users Across the Globe
              </div>
            </div>
          </div>
        </Motion.motion.div>
      </div>

      {/* Partners (delay 1.4s) */}
      <Motion.motion.div
        {...baseAnimation}
        transition={{ ...commonTransition, delay: 1.4 }}
        className="z-10 flex flex-col items-center gap-6 pb-12 mt-12 px-4"
      >
        <div className="liquid-glass rounded-full px-3.5 py-1 text-xs font-medium text-white/95 font-body">
          Collaborating with top aerospace pioneers globally
        </div>
        <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 font-heading italic text-white text-2xl md:text-3xl tracking-tight leading-none">
          <span>Aeon</span>
          <span>·</span>
          <span>Vela</span>
          <span>·</span>
          <span>Apex</span>
          <span>·</span>
          <span>Orbit</span>
          <span>·</span>
          <span>Zeno</span>
        </div>
      </Motion.motion.div>
    </section>
  );
};

window.Hero = Hero;
