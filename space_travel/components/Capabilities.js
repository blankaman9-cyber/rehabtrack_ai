const AISceneryIcon = () => (
  <svg viewBox="0 0 24 24" className="h-6 w-6 text-white" fill="currentColor">
    <path d="M5 21q-.825 0-1.412-.587T3 19V5q0-.825.588-1.412T5 3h14q.825 0 1.413.588T21 5v14q0 .825-.587 1.413T19 21H5Zm1-4h12l-3.75-5-3 4L9 13l-3 4Z"/>
  </svg>
);

const BatchProductionIcon = () => (
  <svg viewBox="0 0 24 24" className="h-6 w-6 text-white" fill="currentColor">
    <path d="M4 6.47 5.76 10H20v8H4V6.47M22 4h-4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.89-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4Z"/>
  </svg>
);

const SmartLightingIcon = () => (
  <svg viewBox="0 0 24 24" className="h-6 w-6 text-white" fill="currentColor">
    <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1Zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7Z"/>
  </svg>
);

const Capabilities = () => {
  const cards = [
    {
      title: "AI Scenery",
      body: "AI analyzes your product to create indistinguishable natural environments — from Icelandic cliffs to misty forests.",
      icon: <AISceneryIcon />,
      tags: ["Natural Context", "Photo Realism", "Infinite Settings", "Eco-Vibe"]
    },
    {
      title: "Batch Production",
      body: "Style your entire product line in minutes. Create a unified visual identity for catalogues and social media without weeks of retouching.",
      icon: <BatchProductionIcon />,
      tags: ["Scale Fast", "Visual Consistency", "Time Saver", "Ready to Post"]
    },
    {
      title: "Smart Lighting",
      body: "Automatic lighting and material adjustment. Achieve flawless integration with realistic shadows and sunlight.",
      icon: <SmartLightingIcon />,
      tags: ["Ray Tracing", "Physical Shadows", "Studio Quality", "Sunlight Sync"]
    }
  ];

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.15
      }
    }
  };

  const cardVariants = {
    hidden: { filter: "blur(10px)", opacity: 0, y: 30 },
    visible: {
      filter: "blur(0px)",
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, ease: "easeOut" }
    }
  };

  return (
    <section id="voyages" className="relative min-h-screen bg-black overflow-hidden flex flex-col justify-between z-10">
      {/* Background video (full-bleed, no 120% scale) */}
      <FadingVideo
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_094631_d30ab262-45ee-4b7d-99f3-5d5848c8ef13.mp4"
        className="absolute inset-0 w-full h-full object-cover z-0"
      />

      {/* Content */}
      <div className="relative z-10 px-8 md:px-16 lg:px-20 pt-28 pb-16 flex flex-col min-h-screen">
        {/* Header */}
        <div className="mb-auto">
          <Motion.motion.div
            initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
            whileInView={{ filter: "blur(0px)", opacity: 0.8, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-sm font-body text-white mb-6 uppercase tracking-wider"
          >
            // Capabilities
          </Motion.motion.div>
          <Motion.motion.h2
            initial={{ filter: "blur(10px)", opacity: 0, y: 35 }}
            whileInView={{ filter: "blur(0px)", opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.1, ease: "easeOut" }}
            className="font-heading italic text-white text-6xl md:text-7xl lg:text-[6rem] leading-[0.9] tracking-[-3px]"
          >
            Production<br />evolved
          </Motion.motion.h2>
        </div>

        {/* Three cards */}
        <Motion.motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16"
        >
          {cards.map((card, i) => (
            <Motion.motion.div
              key={i}
              variants={cardVariants}
              className="liquid-glass rounded-[1.25rem] p-6 min-h-[360px] flex flex-col justify-between group hover:border-white/10 transition-colors"
            >
              {/* Top row */}
              <div className="flex items-start justify-between gap-4">
                {/* Icon box (44x44 liquid glass square) */}
                <div className="w-11 h-11 rounded-[0.75rem] liquid-glass flex items-center justify-center text-white shrink-0">
                  {card.icon}
                </div>
                {/* Tags row */}
                <div className="flex flex-wrap justify-end gap-1.5 max-w-[70%]">
                  {card.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Bottom section */}
              <div className="mt-6">
                <h3 className="font-heading italic text-white text-3xl md:text-4xl tracking-[-1px] leading-none mb-3">
                  {card.title}
                </h3>
                <p className="text-sm text-white/90 font-body font-light leading-snug max-w-[32ch]">
                  {card.body}
                </p>
              </div>
            </Motion.motion.div>
          ))}
        </Motion.motion.div>
      </div>
    </section>
  );
};

window.Capabilities = Capabilities;
