const RoleSelection = ({ onSelectRole }) => {
  return (
    <div className="relative min-h-screen flex flex-col justify-center items-center text-center px-4 overflow-hidden">
      {/* Background Video */}
      <FadingVideo
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_080021_d598092b-c4c2-4e53-8e46-94cf9064cd50.mp4"
        className="absolute inset-0 w-full h-full object-cover z-0"
      />
      <div className="absolute inset-0 bg-black/60 z-0" />

      {/* Main Container */}
      <div className="relative z-10 max-w-4xl w-full flex flex-col items-center">

        {/* Title */}
        <h1 className="font-heading italic text-6xl md:text-7xl lg:text-8xl text-white leading-none tracking-tight mb-3">
          RehabTrack
        </h1>

        {/* Subtitle */}
        <p className="font-body font-light text-white/70 text-base md:text-lg max-w-lg mb-12">
          AI-powered telerehabilitation with real-time pose tracking, clinical analytics, and LSTM-driven exercise validation.
        </p>

        {/* Role Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-2xl px-4">
          {/* Patient Card */}
          <div
            onClick={() => onSelectRole("patient")}
            className="group liquid-glass rounded-[1.5rem] p-8 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 hover:scale-105 hover:bg-white/[0.03] hover:shadow-[0_8px_30px_rgba(255,255,255,0.05)]"
          >
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">🏃</div>
            <h2 className="font-heading italic text-3xl text-white mb-2">Patient Portal</h2>
            <p className="font-body font-light text-sm text-white/60 leading-relaxed max-w-[24ch]">
              Start your recovery session with real-time camera tracking and instant form scoring.
            </p>
          </div>

          {/* Doctor Card */}
          <div
            onClick={() => onSelectRole("doctor")}
            className="group liquid-glass rounded-[1.5rem] p-8 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 hover:scale-105 hover:bg-white/[0.03] hover:shadow-[0_8px_30px_rgba(255,255,255,0.05)]"
          >
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">🩺</div>
            <h2 className="font-heading italic text-3xl text-white mb-2">Doctor Portal</h2>
            <p className="font-body font-light text-sm text-white/60 leading-relaxed max-w-[24ch]">
              Analyze patient range of motion metrics, prescription logs, and compliance.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

window.RoleSelection = RoleSelection;
