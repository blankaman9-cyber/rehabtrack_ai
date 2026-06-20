const Login = ({ role, onLoginSuccess, onBack }) => {
  const [name, setName] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [isRegistering, setIsRegistering] = React.useState(false);
  const [age, setAge] = React.useState(30);
  const [condition, setCondition] = React.useState("");
  const [specialty, setSpecialty] = React.useState("");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !password) {
      setError("Please fill in name and password.");
      return;
    }

    if (isRegistering) {
      if (isPatient) {
        if (!age || !condition) {
          setError("Please fill in age and condition.");
          return;
        }
      } else {
        if (!specialty) {
          setError("Please fill in specialty.");
          return;
        }
      }
    }

    setLoading(true);
    setError("");

    try {
      if (isRegistering) {
        const url = isPatient ? "/api/patients" : "/api/doctors";
        const body = isPatient 
          ? { name, age: Number(age), condition, password }
          : { name, password, specialty };

        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        
        if (res.ok && data.id) {
          // Success: Auto login
          const loggedUser = isPatient
            ? { id: data.id, name, age: Number(age), condition, role: "patient" }
            : { id: data.id, name, specialty, role: "doctor" };
          onLoginSuccess(loggedUser);
        } else {
          setError(data.error || "Registration failed.");
        }
      } else {
        // Sign In
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role, name, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          onLoginSuccess(data.user);
        } else {
          setError(data.error || "Invalid name or password.");
        }
      }
    } catch (err) {
      console.error(err);
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const isPatient = role === "patient";

  return (
    <div className="relative min-h-screen flex flex-col justify-center items-center px-4 overflow-hidden">
      {/* Background Video */}
      <FadingVideo
        src={
          isPatient
            ? "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_080021_d598092b-c4c2-4e53-8e46-94cf9064cd50.mp4"
            : "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_094631_d30ab262-45ee-4b7d-99f3-5d5848c8ef13.mp4"
        }
        className="absolute inset-0 w-full h-full object-cover z-0"
      />
      <div className="absolute inset-0 bg-black/75 z-0" />

      {/* Login / Register Card */}
      <div className="relative z-10 max-w-md w-full px-4">
        <div className="liquid-glass-strong rounded-[2rem] p-8 md:p-10 flex flex-col items-center shadow-2xl">
          {/* Role Icon */}
          <div className="text-5xl mb-6 select-none animate-pulse">
            {isPatient ? "🏃" : "🩺"}
          </div>

          {/* Heading */}
          <h2 className="font-heading italic text-4xl text-white mb-2 tracking-tight text-center">
            {isRegistering
              ? (isPatient ? "Patient Sign Up" : "Doctor Sign Up")
              : (isPatient ? "Patient Sign In" : "Doctor Sign In")}
          </h2>
          <p className="font-body font-light text-white/60 text-xs mb-8 text-center max-w-[28ch]">
            {isRegistering
              ? "Create a new portal account and set your access credentials."
              : (isPatient
                  ? "Access your personal recovery exercises and tracking session history."
                  : "Review patient analytics, compliance metrics, and update prescriptions.")}
          </p>

          {/* Error Message */}
          {error && (
            <div className="w-full bg-red-500/10 border border-red-500/20 text-red-200 text-xs font-body rounded-full px-4 py-2.5 mb-6 text-center">
              ⚠️ {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
            <div>
              <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-2 font-medium pl-3">
                Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={isPatient ? "e.g. Arjun Sharma" : "e.g. Dr. Sarah Jenkins"}
                className="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 transition-all font-body"
                disabled={loading}
                required
              />
            </div>

            <div>
              <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-2 font-medium pl-3">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 transition-all font-body"
                disabled={loading}
                required
              />
            </div>

            {/* Patient Fields for Signup */}
            {isRegistering && isPatient && (
              <React.Fragment>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-2 font-medium pl-3">
                    Age
                  </label>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(Number(e.target.value))}
                    min="5"
                    max="110"
                    className="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white focus:outline-none focus:border-white/30 transition-all font-body"
                    disabled={loading}
                    required
                  />
                </div>

                <div>
                  <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-2 font-medium pl-3">
                    Condition / Diagnosis
                  </label>
                  <input
                    type="text"
                    value={condition}
                    onChange={(e) => setCondition(e.target.value)}
                    placeholder="e.g. Knee osteoarthritis"
                    className="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 transition-all font-body"
                    disabled={loading}
                    required
                  />
                </div>
              </React.Fragment>
            )}

            {/* Doctor Fields for Signup */}
            {isRegistering && !isPatient && (
              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-2 font-medium pl-3">
                  Specialty / Department
                </label>
                <input
                  type="text"
                  value={specialty}
                  onChange={(e) => setSpecialty(e.target.value)}
                  placeholder="e.g. Physical Therapist"
                  className="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 transition-all font-body"
                  disabled={loading}
                  required
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full liquid-glass-strong rounded-full py-3.5 text-sm font-semibold tracking-wide text-white hover:bg-white/5 transition-all mt-4 flex items-center justify-center gap-2"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                isRegistering ? "Register & Sign In" : "Sign In"
              )}
            </button>
          </form>

          {/* Toggle Register/Login Option */}
          <button
            type="button"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError("");
            }}
            className="text-xs text-white/50 hover:text-white transition-colors font-body mt-5 text-center w-full"
            disabled={loading}
          >
            {isRegistering ? "Already have an account? Sign In" : "Don't have an account? Register here"}
          </button>

          {/* Back button */}
          <button
            onClick={onBack}
            className="text-xs text-white/30 hover:text-white/80 transition-colors font-body mt-5"
            disabled={loading}
          >
            ← Back to portals
          </button>
        </div>
      </div>
    </div>
  );
};

window.Login = Login;
